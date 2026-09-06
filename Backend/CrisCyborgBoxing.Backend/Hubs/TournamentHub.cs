using CrisCyborgBoxing.Backend.Data;
using CrisCyborgBoxing.Backend.Models;
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;

namespace CrisCyborgBoxing.Backend.Hubs;

public class TournamentHub : Hub
{
    private readonly AppDbContext _dbContext;
    private readonly ILogger<TournamentHub> _logger;

    public TournamentHub(AppDbContext dbContext, ILogger<TournamentHub> logger)
    {
        _dbContext = dbContext;
        _logger = logger;
    }

    public async Task JoinTournament(int tournamentId, int playerId)
    {
        try
        {
            await Groups.AddToGroupAsync(Context.ConnectionId, $"tournament_{tournamentId}");
            await Clients.Group($"tournament_{tournamentId}").SendAsync("PlayerJoinedTournament", playerId);
            _logger.LogInformation($"Player {playerId} watching tournament {tournamentId}");
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error joining tournament: {ex.Message}");
        }
    }

    public async Task BracketUpdate(int tournamentId, string bracketJson)
    {
        try
        {
            await Clients.Group($"tournament_{tournamentId}").SendAsync("BracketUpdated", bracketJson);
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error updating bracket: {ex.Message}");
        }
    }

    public async Task LeaderboardUpdate(int tournamentId)
    {
        try
        {
            var leaderboard = await _dbContext.TournamentEntries
                .Where(e => e.TournamentId == tournamentId)
                .Include(e => e.Player)
                .OrderBy(e => e.Ranking)
                .ToListAsync();

            await Clients.Group($"tournament_{tournamentId}").SendAsync("LeaderboardUpdated", leaderboard);
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error updating leaderboard: {ex.Message}");
        }
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        _logger.LogWarning($"Client disconnected: {Context.ConnectionId}");
        await base.OnDisconnectedAsync(exception);
    }
}
