using CrisCyborgBoxing.Backend.Data;
using CrisCyborgBoxing.Backend.Models;
using CrisCyborgBoxing.Backend.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace CrisCyborgBoxing.Backend.Controllers;

[ApiController]
[Route("api/[controller]")]
public class PlayersController : ControllerBase
{
    private readonly AppDbContext _dbContext;
    private readonly IRewardService _rewardService;
    private readonly ILogger<PlayersController> _logger;

    public PlayersController(
        AppDbContext dbContext,
        IRewardService rewardService,
        ILogger<PlayersController> logger)
    {
        _dbContext = dbContext;
        _rewardService = rewardService;
        _logger = logger;
    }

    [HttpGet("{id}")]
    public async Task<IActionResult> GetPlayer(int id)
    {
        try
        {
            var player = await _dbContext.Players.FindAsync(id);
            if (player == null)
                return NotFound(new { error = "Player not found" });

            return Ok(new PlayerDto
            {
                Id = player.Id,
                MetaMaskAddress = player.MetaMaskAddress,
                Username = player.Username,
                SkillLevel = player.SkillLevel,
                Wins = player.Wins,
                Losses = player.Losses,
                Balance = player.Balance
            });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching player: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpGet("leaderboard")]
    public async Task<IActionResult> GetLeaderboard(int skip = 0, int take = 100)
    {
        try
        {
            var leaderboard = await _dbContext.Players
                .Where(p => p.IsActive)
                .OrderByDescending(p => p.Wins)
                .ThenBy(p => p.Losses)
                .Skip(skip)
                .Take(take)
                .Select(p => new
                {
                    p.Id,
                    p.Username,
                    p.SkillLevel,
                    p.Wins,
                    p.Losses,
                    WinRate = (p.Wins + p.Losses) > 0 ? (decimal)p.Wins / (p.Wins + p.Losses) : 0
                })
                .ToListAsync();

            return Ok(leaderboard);
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching leaderboard: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpGet("{id}/balance")]
    public async Task<IActionResult> GetPlayerBalance(int id)
    {
        try
        {
            var player = await _dbContext.Players.FindAsync(id);
            if (player == null)
                return NotFound(new { error = "Player not found" });

            // Get blockchain balance
            var blockchainBalance = await _rewardService.GetPlayerBlockchainBalanceAsync(player.MetaMaskAddress);

            return Ok(new
            {
                playerId = player.Id,
                localBalance = player.Balance,
                blockchainBalance = blockchainBalance,
                totalBalance = player.Balance + blockchainBalance
            });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching balance: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpGet("{id}/stats")]
    public async Task<IActionResult> GetPlayerStats(int id)
    {
        try
        {
            var player = await _dbContext.Players
                .Include(p => p.MatchesAsPlayer1)
                .Include(p => p.MatchesAsPlayer2)
                .FirstOrDefaultAsync(p => p.Id == id);

            if (player == null)
                return NotFound(new { error = "Player not found" });

            var totalMatches = player.MatchesAsPlayer1.Count + player.MatchesAsPlayer2.Count;
            var winRate = totalMatches > 0 ? (decimal)player.Wins / totalMatches : 0;

            return Ok(new
            {
                player.Username,
                player.SkillLevel,
                player.Wins,
                player.Losses,
                totalMatches,
                winRate,
                player.Balance,
                player.CreatedAt,
                player.LastLoginAt
            });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching player stats: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }
}
