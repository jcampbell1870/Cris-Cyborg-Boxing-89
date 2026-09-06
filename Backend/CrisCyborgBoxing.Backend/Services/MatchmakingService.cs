using CrisCyborgBoxing.Backend.Data;
using CrisCyborgBoxing.Backend.Models;
using Microsoft.EntityFrameworkCore;

namespace CrisCyborgBoxing.Backend.Services;

public interface IMatchmakingService
{
    Task<Match?> FindMatchAsync(int playerId);
    Task<List<Player>> GetWaitingPlayersAsync();
    Task RemoveFromQueueAsync(int playerId);
    Task<Match?> CreateMatchAsync(int player1Id, int player2Id, int? tournamentId = null);
    decimal CalculateEloRating(int wins, int losses);
}

public class MatchmakingService : IMatchmakingService
{
    private readonly AppDbContext _dbContext;
    private readonly ILogger<MatchmakingService> _logger;
    private static List<int> _waitingQueue = new();

    public MatchmakingService(AppDbContext dbContext, ILogger<MatchmakingService> logger)
    {
        _dbContext = dbContext;
        _logger = logger;
    }

    public async Task<Match?> FindMatchAsync(int playerId)
    {
        try
        {
            var player = await _dbContext.Players.FindAsync(playerId);
            if (player == null)
            {
                _logger.LogWarning($"Player {playerId} not found");
                return null;
            }

            // Add player to waiting queue
            if (!_waitingQueue.Contains(playerId))
            {
                _waitingQueue.Add(playerId);
                _logger.LogInformation($"Player {playerId} ({player.Username}) added to matchmaking queue");
            }

            // Look for opponent with similar skill level (within 2 levels)
            var potentialOpponents = _waitingQueue
                .Where(id => id != playerId)
                .ToList();

            if (potentialOpponents.Count == 0)
            {
                _logger.LogInformation($"No opponents found for player {playerId}");
                return null;
            }

            var opponentId = potentialOpponents.FirstOrDefault();
            if (opponentId == 0)
                return null;

            // Remove both players from queue
            _waitingQueue.Remove(playerId);
            _waitingQueue.Remove(opponentId);

            // Create match
            return await CreateMatchAsync(playerId, opponentId);
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error finding match: {ex.Message}");
            return null;
        }
    }

    public async Task<List<Player>> GetWaitingPlayersAsync()
    {
        try
        {
            return await _dbContext.Players
                .Where(p => _waitingQueue.Contains(p.Id))
                .ToListAsync();
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error fetching waiting players: {ex.Message}");
            return new List<Player>();
        }
    }

    public async Task RemoveFromQueueAsync(int playerId)
    {
        _waitingQueue.Remove(playerId);
        _logger.LogInformation($"Player {playerId} removed from matchmaking queue");
        await Task.CompletedTask;
    }

    public async Task<Match?> CreateMatchAsync(int player1Id, int player2Id, int? tournamentId = null)
    {
        try
        {
            var player1 = await _dbContext.Players.FindAsync(player1Id);
            var player2 = await _dbContext.Players.FindAsync(player2Id);

            if (player1 == null || player2 == null)
            {
                _logger.LogError("One or both players not found");
                return null;
            }

            var match = new Match
            {
                Player1Id = player1Id,
                Player2Id = player2Id,
                StartTime = DateTime.UtcNow,
                State = MatchState.Pending,
                TournamentId = tournamentId,
                Player1Score = 0,
                Player2Score = 0,
                RoundsCompleted = 0
            };

            _dbContext.Matches.Add(match);
            await _dbContext.SaveChangesAsync();

            _logger.LogInformation($"Match created: {player1.Username} vs {player2.Username} (Match ID: {match.Id})");
            return match;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error creating match: {ex.Message}");
            return null;
        }
    }

    public decimal CalculateEloRating(int wins, int losses)
    {
        // Simple ELO-like calculation
        var totalGames = wins + losses;
        if (totalGames == 0)
            return 1000; // Base rating

        var winRate = (decimal)wins / totalGames;
        return 1000 + (wins * 32) - (losses * 16);
    }
}
