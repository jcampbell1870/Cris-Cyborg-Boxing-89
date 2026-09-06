using CrisCyborgBoxing.Backend.Models;
using CrisCyborgBoxing.Backend.Services;
using Microsoft.AspNetCore.Mvc;

namespace CrisCyborgBoxing.Backend.Controllers;

[ApiController]
[Route("api/[controller]")]
public class RewardsController : ControllerBase
{
    private readonly IRewardService _rewardService;
    private readonly ILogger<RewardsController> _logger;

    public RewardsController(IRewardService rewardService, ILogger<RewardsController> logger)
    {
        _rewardService = rewardService;
        _logger = logger;
    }

    [HttpPost("claim")]
    public async Task<IActionResult> ClaimReward([FromBody] dynamic request)
    {
        try
        {
            int playerId = request?.playerId ?? 0;
            decimal amount = request?.amount ?? 0;
            string rewardTypeStr = request?.rewardType ?? "MatchWin";

            if (playerId == 0 || amount <= 0)
                return BadRequest(new { error = "Invalid request parameters" });

            if (!Enum.TryParse<RewardType>(rewardTypeStr, out var rewardType))
                rewardType = RewardType.MatchWin;

            var reward = await _rewardService.DistributeRewardAsync(playerId, amount, rewardType);
            if (reward == null)
                return StatusCode(500, new { error = "Failed to distribute reward" });

            return Ok(new
            {
                rewardId = reward.Id,
                amount = reward.Amount,
                status = reward.Status,
                transactionHash = reward.TransactionHash
            });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error claiming reward: {ex.Message}");
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
