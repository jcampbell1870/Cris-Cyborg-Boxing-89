using CrisCyborgBoxing.Backend.Models;
using CrisCyborgBoxing.Backend.Services;
using Microsoft.AspNetCore.Mvc;

namespace CrisCyborgBoxing.Backend.Controllers;

[ApiController]
[Route("api/[controller]")]
public class MatchesController : ControllerBase
{
    private readonly IMatchmakingService _matchmakingService;
    private readonly IRewardService _rewardService;
    private readonly ILogger<MatchesController> _logger;

    public MatchesController(
        IMatchmakingService matchmakingService,
        IRewardService rewardService,
        ILogger<MatchesController> logger)
    {
        _matchmakingService = matchmakingService;
        _rewardService = rewardService;
        _logger = logger;
    }

    [HttpPost("findmatch")]
    public async Task<IActionResult> FindMatch([FromBody] dynamic request)
    {
        try
        {
            int playerId = request?.playerId ?? 0;
            if (playerId == 0)
                return BadRequest(new { error = "Invalid player ID" });

            var match = await _matchmakingService.FindMatchAsync(playerId);
            if (match == null)
                return NotFound(new { message = "No opponent found. Please wait..." });

            return Ok(new
            {
                matchId = match.Id,
                player1Id = match.Player1Id,
                player2Id = match.Player2Id,
                startTime = match.StartTime
            });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error finding match: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpGet("queue")]
    public async Task<IActionResult> GetQueue()
    {
        try
        {
            var waitingPlayers = await _matchmakingService.GetWaitingPlayersAsync();
            return Ok(new
            {
                playersWaiting = waitingPlayers.Count,
                players = waitingPlayers.Select(p => new { p.Id, p.Username, p.SkillLevel }).ToList()
            });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching queue: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpPost("{id}/cancelqueue")]
    public async Task<IActionResult> CancelQueueWait(int id)
    {
        try
        {
            await _matchmakingService.RemoveFromQueueAsync(id);
            return Ok(new { message = "Removed from queue" });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error canceling queue: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }
}
