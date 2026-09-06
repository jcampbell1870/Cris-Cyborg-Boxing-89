using CrisCyborgBoxing.Backend.Configuration;
using CrisCyborgBoxing.Backend.Data;
using CrisCyborgBoxing.Backend.Models;
using Nethereum.Web3;
using Nethereum.Web3.Accounts;
using Nethereum.StandardTokenABI;
using System.Numerics;
using Nethereum.RPC.Eth.DTOs;

namespace CrisCyborgBoxing.Backend.Services;

public interface IRewardService
{
    Task<Reward?> DistributeRewardAsync(int playerId, decimal amount, RewardType rewardType, int? matchId = null);
    Task<decimal> GetPlayerBlockchainBalanceAsync(string walletAddress);
    Task<bool> CompleteRewardAsync(int rewardId, string transactionHash);
    Task<List<Reward>> GetPlayerRewardsAsync(int playerId);
    Task RetryFailedRewardsAsync();
}

public class RewardService : IRewardService
{
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

        // Initialize Web3 with RPC endpoint
        _web3 = new Web3(_blockchainConfig.RpcUrl);
    }

    public async Task<Reward?> DistributeRewardAsync(int playerId, decimal amount, RewardType rewardType, int? matchId = null)
    {
        try
        {
            var player = await _dbContext.Players.FindAsync(playerId);
            if (player == null)
            {
                _logger.LogError($"Player {playerId} not found");
                return null;
            }

            // Create reward record
            var reward = new Reward
            {
                PlayerId = playerId,
                Amount = amount,
                Status = RewardStatus.Processing,
                RewardType = rewardType,
                MatchId = matchId,
                CreatedAt = DateTime.UtcNow
            };

            _dbContext.Rewards.Add(reward);
            await _dbContext.SaveChangesAsync();

            // Distribute token via Nethereum
            var txHash = await TransferTokenAsync(player.MetaMaskAddress, amount);

            if (!string.IsNullOrEmpty(txHash))
            {
                reward.TransactionHash = txHash;
                reward.Status = RewardStatus.Completed;
                reward.CompletedAt = DateTime.UtcNow;

                // Update player balance
                player.Balance += amount;
                _dbContext.Update(player);
            }
            else
            {
                reward.Status = RewardStatus.Failed;
                reward.ErrorMessage = "Transaction failed";
            }

            _dbContext.Update(reward);
            await _dbContext.SaveChangesAsync();

            _logger.LogInformation($"Reward distributed: {amount} 1870Coin to {player.Username} (ID: {playerId})");
            return reward;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error distributing reward: {ex.Message}");
            return null;
        }
    }

    private async Task<string?> TransferTokenAsync(string recipientAddress, decimal amount)
    {
        try
        {
            // Load account with private key (should be in Azure Key Vault in production)
            var account = new Account(_blockchainConfig.PrivateKey, _blockchainConfig.ChainId);
            var web3 = new Web3(account, _blockchainConfig.RpcUrl);

            // Get contract handler
            var contractAddress = _blockchainConfig.ContractAddress;
            var contract = web3.Eth.GetContract(StandardTokenABI.ABI, contractAddress);

            // Get transfer function
            var transferFunction = contract.GetFunction("transfer");

            // Convert amount to Wei (assuming 18 decimals for ERC-20)
            var amountInWei = Web3.Convert.ToWei(amount, 18);

            // Execute transfer
            var transactionHash = await transferFunction.SendTransactionAsync(
                account.Address,
                new Nethereum.RPC.Eth.DTOs.TransactionInput(),
                recipientAddress,
                (BigInteger)amountInWei);

            _logger.LogInformation($"Transfer transaction initiated: {transactionHash}");
            return transactionHash;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error transferring tokens: {ex.Message}");
            return null;
        }
    }

    public async Task<decimal> GetPlayerBlockchainBalanceAsync(string walletAddress)
    {
        try
        {
            var contractAddress = _blockchainConfig.ContractAddress;
            var contract = _web3.Eth.GetContract(StandardTokenABI.ABI, contractAddress);

            var balanceFunction = contract.GetFunction("balanceOf");
            var balance = await balanceFunction.CallAsync<BigInteger>(walletAddress);

            // Convert from Wei to tokens (18 decimals)
            return Web3.Convert.FromWei(balance, 18);
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

                var txHash = await TransferTokenAsync(reward.Player.MetaMaskAddress, reward.Amount);
                if (!string.IsNullOrEmpty(txHash))
                {
                    reward.TransactionHash = txHash;
                    reward.Status = RewardStatus.Completed;
                    reward.CompletedAt = DateTime.UtcNow;
                    _dbContext.Update(reward);
                }
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
