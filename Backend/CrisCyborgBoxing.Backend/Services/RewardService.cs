using System.Numerics;
using System.Text;
using CrisCyborgBoxing.Backend.Configuration;
using CrisCyborgBoxing.Backend.Data;
using CrisCyborgBoxing.Backend.Models;
using Microsoft.EntityFrameworkCore;
using Nethereum.Hex.HexConvertors.Extensions;
using Nethereum.Signer;
using Nethereum.Util;
using Nethereum.Web3;

namespace CrisCyborgBoxing.Backend.Services;

public interface IRewardService
{
    Task<Reward?> DistributeRewardAsync(int playerId, RewardType rewardType, int? matchId = null);
    Task<decimal> GetPlayerBlockchainBalanceAsync(string walletAddress);
    Task<bool> CompleteRewardAsync(int rewardId, string transactionHash);
    Task<List<Reward>> GetPlayerRewardsAsync(int playerId);
    Task RetryFailedRewardsAsync();
}

/// <summary>
/// Issues Arcade1870 (ARC) token rewards using the same non-custodial pattern
/// as Crypto Chess: a dedicated reward signer produces an EIP-712 signature
/// authorizing the player to claim ARC directly from the shared, pre-funded
/// Arcade1870RewardVault contract. The player submits the claim transaction
/// themselves and pays their own gas - this backend never holds ARC funds or
/// a custodial transfer key.
/// </summary>
public class RewardService : IRewardService
{
    private const string ClaimTypeHash =
        "Claim(address recipient,uint256 amount,uint256 nonce,uint256 deadline)";
    private const string DomainTypeHash =
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)";
    private const string VaultDomainName = "Arcade1870RewardVault";
    private const string VaultDomainVersion = "1";

    private static readonly string MinimalErc20Abi = @"[
        { 'constant': true, 'inputs': [{'name': '_owner', 'type': 'address'}], 'name': 'balanceOf', 'outputs': [{'name': 'balance', 'type': 'uint256'}], 'type': 'function' }
    ]".Replace('\'', '"');

    private readonly AppDbContext _dbContext;
    private readonly BlockchainConfig _blockchainConfig;
    private readonly ILogger<RewardService> _logger;
    private readonly IWeb3 _web3;

    public RewardService(
        AppDbContext dbContext,
        BlockchainConfig blockchainConfig,
        ILogger<RewardService> logger)
    {
        _dbContext = dbContext;
        _blockchainConfig = blockchainConfig;
        _logger = logger;

        // Initialize Web3 with RPC endpoint for read-only balance lookups.
        _web3 = new Web3(_blockchainConfig.RpcUrl);
    }

    public async Task<Reward?> DistributeRewardAsync(int playerId, RewardType rewardType, int? matchId = null)
    {
        try
        {
            var player = await _dbContext.Players.FindAsync(playerId);
            if (player == null)
            {
                _logger.LogError($"Player {playerId} not found");
                return null;
            }

            if (string.IsNullOrEmpty(_blockchainConfig.RewardVaultAddress) ||
                string.IsNullOrEmpty(_blockchainConfig.RewardSignerPrivateKey))
            {
                _logger.LogError("Arcade1870RewardVault is not configured (missing vault address or reward signer key)");
                return null;
            }

            // Enforce the minimum interval between reward claims per player,
            // regardless of reward type, to prevent claim spamming.
            var lastReward = await _dbContext.Rewards
                .Where(r => r.PlayerId == playerId)
                .OrderByDescending(r => r.CreatedAt)
                .FirstOrDefaultAsync();
            if (lastReward != null &&
                (DateTime.UtcNow - lastReward.CreatedAt).TotalMilliseconds < _blockchainConfig.MinClaimIntervalMs)
            {
                _logger.LogWarning($"Player {playerId} attempted to claim a reward before the minimum claim interval elapsed");
                return null;
            }

            // The reward amount is always determined server-side from the
            // reward type, never trusted from the caller, so a client cannot
            // request an arbitrarily large signed claim.
            var resolvedAmount = ResolveRewardAmount(rewardType);

            // Create reward record
            var reward = new Reward
            {
                PlayerId = playerId,
                Amount = resolvedAmount,
                Status = RewardStatus.Processing,
                RewardType = rewardType,
                MatchId = matchId,
                CreatedAt = DateTime.UtcNow
            };

            _dbContext.Rewards.Add(reward);
            await _dbContext.SaveChangesAsync();

            var claim = IssueVaultClaim(player.MetaMaskAddress, resolvedAmount);

            reward.Nonce = claim.Nonce.ToString();
            reward.Deadline = claim.Deadline;
            reward.Signature = claim.Signature;
            reward.Status = RewardStatus.Issued;

            _dbContext.Update(reward);
            await _dbContext.SaveChangesAsync();

            _logger.LogInformation($"Reward claim issued: {resolvedAmount} ARC to {player.Username} (ID: {playerId})");
            return reward;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error distributing reward: {ex.Message}");
            return null;
        }
    }

    /// <summary>
    /// Maps a reward type to a fixed ARC amount, relative to the configured
    /// base <see cref="BlockchainConfig.RewardAmount"/>. Never trust a
    /// client-supplied amount for a signed vault claim.
    /// </summary>
    private decimal ResolveRewardAmount(RewardType rewardType)
    {
        var baseAmount = _blockchainConfig.RewardAmount;
        return rewardType switch
        {
            RewardType.MatchWin => baseAmount,
            RewardType.TournamentVictory => baseAmount * 5,
            RewardType.DailyBonus => baseAmount / 2,
            RewardType.ReferralBonus => baseAmount,
            _ => baseAmount
        };
    }

    /// <summary>
    /// Signs an EIP-712 "Claim(address recipient,uint256 amount,uint256 nonce,uint256 deadline)"
    /// message for the Arcade1870RewardVault contract, matching the domain
    /// (name "Arcade1870RewardVault", version "1", the configured chain ID and
    /// vault address) that the vault verifies on-chain.
    /// </summary>
    private (BigInteger Nonce, long Deadline, string Signature) IssueVaultClaim(string recipientAddress, decimal amount)
    {
        var amountInWei = Web3.Convert.ToWei(amount, _blockchainConfig.TokenDecimals);
        var nonce = GenerateNonce();
        var deadline = DateTimeOffset.UtcNow.ToUnixTimeSeconds() + _blockchainConfig.ClaimTtlSeconds;

        var domainSeparator = ComputeDomainSeparator();
        var structHash = Sha3Keccack.Current.CalculateHash(Concat(
            Sha3Keccack.Current.CalculateHash(Encoding.UTF8.GetBytes(ClaimTypeHash)),
            AddressToWord(recipientAddress),
            UintToWord(amountInWei),
            UintToWord(nonce),
            UintToWord(deadline)));

        var digest = Sha3Keccack.Current.CalculateHash(Concat(
            new byte[] { 0x19, 0x01 },
            domainSeparator,
            structHash));

        var signerKey = new EthECKey(_blockchainConfig.RewardSignerPrivateKey);
        var signature = signerKey.SignAndCalculateV(digest);

        var signatureBytes = Concat(signature.R, signature.S, new[] { signature.V[0] });
        return (nonce, deadline, "0x" + signatureBytes.ToHex());
    }

    /// <summary>
    /// Generates a cryptographically random, effectively collision-free
    /// nonce for the vault claim (the vault tracks used nonces per
    /// recipient, so any sufficiently random 256-bit value is safe).
    /// </summary>
    private static BigInteger GenerateNonce()
    {
        var randomBytes = System.Security.Cryptography.RandomNumberGenerator.GetBytes(31);
        // Prepend a zero byte so the value is always interpreted as
        // non-negative when read back as a big-endian unsigned BigInteger.
        var unsignedBytes = new byte[32];
        Array.Copy(randomBytes, 0, unsignedBytes, 1, randomBytes.Length);
        return new BigInteger(unsignedBytes, isUnsigned: true, isBigEndian: true);
    }

    private byte[] ComputeDomainSeparator()
    {
        return Sha3Keccack.Current.CalculateHash(Concat(
            Sha3Keccack.Current.CalculateHash(Encoding.UTF8.GetBytes(DomainTypeHash)),
            Sha3Keccack.Current.CalculateHash(Encoding.UTF8.GetBytes(VaultDomainName)),
            Sha3Keccack.Current.CalculateHash(Encoding.UTF8.GetBytes(VaultDomainVersion)),
            UintToWord(_blockchainConfig.ChainId),
            AddressToWord(_blockchainConfig.RewardVaultAddress)));
    }

    private static byte[] UintToWord(BigInteger value)
    {
        // Big-endian, left-padded to 32 bytes (abi.encode of a uint256).
        var bytes = value.ToByteArray(isUnsigned: true, isBigEndian: true);
        var word = new byte[32];
        Array.Copy(bytes, 0, word, 32 - bytes.Length, bytes.Length);
        return word;
    }

    private static byte[] AddressToWord(string address)
    {
        var addressBytes = address.HexToByteArray();
        var word = new byte[32];
        Array.Copy(addressBytes, 0, word, 32 - addressBytes.Length, addressBytes.Length);
        return word;
    }

    private static byte[] Concat(params byte[][] arrays)
    {
        var result = new byte[arrays.Sum(a => a.Length)];
        var offset = 0;
        foreach (var array in arrays)
        {
            Buffer.BlockCopy(array, 0, result, offset, array.Length);
            offset += array.Length;
        }
        return result;
    }

    public async Task<decimal> GetPlayerBlockchainBalanceAsync(string walletAddress)
    {
        try
        {
            var contract = _web3.Eth.GetContract(MinimalErc20Abi, _blockchainConfig.TokenAddress);
            var balanceFunction = contract.GetFunction("balanceOf");
            var balance = await balanceFunction.CallAsync<BigInteger>(walletAddress);

            return Web3.Convert.FromWei(balance, _blockchainConfig.TokenDecimals);
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching blockchain balance: {ex.Message}");
            return 0;
        }
    }

    public async Task<bool> CompleteRewardAsync(int rewardId, string transactionHash)
    {
        try
        {
            var reward = await _dbContext.Rewards.FindAsync(rewardId);
            if (reward == null)
                return false;

            reward.TransactionHash = transactionHash;
            reward.Status = RewardStatus.Completed;
            reward.CompletedAt = DateTime.UtcNow;

            var player = await _dbContext.Players.FindAsync(reward.PlayerId);
            if (player != null)
            {
                player.Balance += reward.Amount;
                _dbContext.Update(player);
            }

            _dbContext.Update(reward);
            await _dbContext.SaveChangesAsync();

            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error completing reward: {ex.Message}");
            return false;
        }
    }

    public async Task<List<Reward>> GetPlayerRewardsAsync(int playerId)
    {
        try
        {
            return await _dbContext.Rewards
                .Where(r => r.PlayerId == playerId)
                .OrderByDescending(r => r.CreatedAt)
                .ToListAsync();
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching player rewards: {ex.Message}");
            return new List<Reward>();
        }
    }

    /// <summary>
    /// Re-issues fresh, unexpired vault claim signatures for rewards that
    /// failed to be issued (e.g. due to a transient signer error). This does
    /// not retry on-chain transfers directly, since claims are always
    /// submitted and paid for by the player's own wallet.
    /// </summary>
    public async Task RetryFailedRewardsAsync()
    {
        try
        {
            var failedRewards = _dbContext.Rewards
                .Where(r => r.Status == RewardStatus.Failed)
                .Include(r => r.Player)
                .ToList();

            foreach (var reward in failedRewards)
            {
                if (reward.Player == null) continue;

                var claim = IssueVaultClaim(reward.Player.MetaMaskAddress, reward.Amount);
                reward.Nonce = claim.Nonce.ToString();
                reward.Deadline = claim.Deadline;
                reward.Signature = claim.Signature;
                reward.Status = RewardStatus.Issued;
                reward.ErrorMessage = null;
                _dbContext.Update(reward);
            }

            await _dbContext.SaveChangesAsync();
            _logger.LogInformation($"Retried {failedRewards.Count} failed rewards");
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error retrying failed rewards: {ex.Message}");
        }
    }
}
