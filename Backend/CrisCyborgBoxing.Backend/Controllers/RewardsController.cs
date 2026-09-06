using CrisCyborgBoxing.Backend.Configuration;
using CrisCyborgBoxing.Backend.Models;
using CrisCyborgBoxing.Backend.Services;
using Microsoft.AspNetCore.Mvc;

namespace CrisCyborgBoxing.Backend.Controllers;

[ApiController]
[Route("api/[controller]")]
public class RewardsController : ControllerBase
{
    private readonly IRewardService _rewardService;
    private readonly BlockchainConfig _blockchainConfig;
    private readonly ILogger<RewardsController> _logger;

    public RewardsController(
        IRewardService rewardService,
        BlockchainConfig blockchainConfig,
        ILogger<RewardsController> logger)
    {
        _rewardService = rewardService;
        _blockchainConfig = blockchainConfig;
        _logger = logger;
    }

    /// <summary>
    /// Issues a signed Arcade1870RewardVault claim for the player. The game
    /// client is responsible for submitting the returned
    /// claim(amount, nonce, deadline, signature) transaction to the vault
    /// itself (paying its own gas), the same non-custodial flow used by
    /// Crypto Chess. This endpoint never transfers ARC directly.
    /// </summary>
    [HttpPost("claim")]
    public async Task<IActionResult> ClaimReward([FromBody] dynamic request)
    {
        try
        {
            int playerId = request?.playerId ?? 0;
            decimal amount = request?.amount ?? (decimal)_blockchainConfig.RewardAmount;
            string rewardTypeStr = request?.rewardType ?? "MatchWin";

            if (playerId == 0 || amount <= 0)
                return BadRequest(new { error = "Invalid request parameters" });

            if (!Enum.TryParse<RewardType>(rewardTypeStr, out var rewardType))
                rewardType = RewardType.MatchWin;

            var reward = await _rewardService.DistributeRewardAsync(playerId, amount, rewardType);
            if (reward == null)
                return StatusCode(500, new { error = "Failed to issue reward claim" });

            return Ok(new
            {
                rewardId = reward.Id,
                amount = reward.Amount,
                status = reward.Status,
                nonce = reward.Nonce,
                deadline = reward.Deadline,
                signature = reward.Signature,
                tokenAddress = _blockchainConfig.TokenAddress,
                rewardVaultAddress = _blockchainConfig.RewardVaultAddress,
                chainId = _blockchainConfig.ChainId,
                chainName = _blockchainConfig.ChainName
            });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error claiming reward: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    /// <summary>
    /// Called by the game client after it has successfully submitted the
    /// signed claim transaction to the Arcade1870RewardVault on-chain, so the
    /// backend can record the resulting transaction hash.
    /// </summary>
    [HttpPost("{rewardId}/complete")]
    public async Task<IActionResult> CompleteReward(int rewardId, [FromBody] dynamic request)
    {
        try
        {
            string? transactionHash = request?.transactionHash;
            if (string.IsNullOrEmpty(transactionHash))
                return BadRequest(new { error = "transactionHash is required" });

            var success = await _rewardService.CompleteRewardAsync(rewardId, transactionHash);
            if (!success)
                return NotFound(new { error = "Reward not found" });

            return Ok(new { rewardId, transactionHash, status = RewardStatus.Completed });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error completing reward: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpGet("{playerId}/history")]
    public async Task<IActionResult> GetRewardHistory(int playerId)
    {
        try
        {
            var rewards = await _rewardService.GetPlayerRewardsAsync(playerId);
            return Ok(rewards.Select(r => new
            {
                r.Id,
                r.Amount,
                r.Status,
                r.RewardType,
                r.TransactionHash,
                r.CreatedAt,
                r.CompletedAt
            }).ToList());
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching reward history: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpGet("{playerId}/balance")]
    public async Task<IActionResult> GetBalance(int playerId, [FromQuery] string walletAddress)
    {
        try
        {
            if (string.IsNullOrEmpty(walletAddress))
                return BadRequest(new { error = "Wallet address required" });

            var balance = await _rewardService.GetPlayerBlockchainBalanceAsync(walletAddress);
            return Ok(new { balance });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching balance: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }
}
