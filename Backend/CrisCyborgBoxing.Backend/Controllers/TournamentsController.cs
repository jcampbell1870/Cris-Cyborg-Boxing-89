using CrisCyborgBoxing.Backend.Models;
using CrisCyborgBoxing.Backend.Services;
using Microsoft.AspNetCore.Mvc;

namespace CrisCyborgBoxing.Backend.Controllers;

[ApiController]
[Route("api/[controller]")]
public class TournamentsController : ControllerBase
{
    private readonly ITournamentService _tournamentService;
    private readonly ILogger<TournamentsController> _logger;

    public TournamentsController(ITournamentService tournamentService, ILogger<TournamentsController> logger)
    {
        _tournamentService = tournamentService;
        _logger = logger;
    }

    [HttpPost("create")]
    public async Task<IActionResult> CreateTournament([FromBody] dynamic request)
    {
        try
        {
            string name = request?.name ?? "";
            int maxPlayers = request?.maxPlayers ?? 0;
            DateTime startTime = request?.startTime ?? DateTime.UtcNow.AddHours(1);

            if (string.IsNullOrEmpty(name) || maxPlayers < 2)
                return BadRequest(new { error = "Invalid tournament parameters" });

            var tournament = await _tournamentService.CreateTournamentAsync(name, maxPlayers, startTime);
            if (tournament == null)
                return StatusCode(500, new { error = "Failed to create tournament" });

            return Ok(new
            {
                tournamentId = tournament.Id,
                name = tournament.Name,
                maxPlayers = tournament.MaxPlayers,
                startTime = tournament.StartTime,
                status = tournament.Status
            });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error creating tournament: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpPost("{id}/register")]
    public async Task<IActionResult> RegisterPlayer(int id, [FromBody] dynamic request)
    {
        try
        {
            int playerId = request?.playerId ?? 0;
            if (playerId == 0)
                return BadRequest(new { error = "Invalid player ID" });

            var success = await _tournamentService.RegisterPlayerInTournamentAsync(id, playerId);
            if (!success)
                return StatusCode(400, new { error = "Failed to register player in tournament" });

            return Ok(new { message = "Player registered in tournament" });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error registering player: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpGet("{id}")]
    public async Task<IActionResult> GetTournament(int id)
    {
        try
        {
            var tournament = await _tournamentService.GetTournamentAsync(id);
            if (tournament == null)
                return NotFound(new { error = "Tournament not found" });

            return Ok(new
            {
                tournament.Id,
                tournament.Name,
                tournament.Description,
                tournament.Status,
                tournament.MaxPlayers,
                tournament.StartTime,
                tournament.EndTime,
                participants = tournament.Entries.Count,
                prizePool = tournament.PrizePool
            });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching tournament: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpGet("active")]
    public async Task<IActionResult> GetActiveTournaments()
    {
        try
        {
            var tournaments = await _tournamentService.GetActiveTournamentsAsync();
            return Ok(tournaments.Select(t => new
            {
                t.Id,
                t.Name,
                t.Status,
                t.MaxPlayers,
                t.StartTime,
                participants = t.Entries.Count,
                t.PrizePool
            }).ToList());
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching tournaments: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpPost("{id}/start")]
    public async Task<IActionResult> StartTournament(int id)
    {
        try
        {
            await _tournamentService.GenerateBracketAsync(id);
            return Ok(new { message = "Tournament started" });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error starting tournament: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpGet("{id}/leaderboard")]
    public async Task<IActionResult> GetLeaderboard(int id)
    {
        try
        {
            var leaderboard = await _tournamentService.GetTournamentLeaderboardAsync(id);
            return Ok(leaderboard.Select((e, index) => new
            {
                rank = index + 1,
                playerId = e.Player?.Id,
                playerName = e.Player?.Username,
                skillLevel = e.Player?.SkillLevel,
                ranking = e.Ranking
            }).ToList());
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching leaderboard: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }
}
