using CrisCyborgBoxing.Backend.Data;
using CrisCyborgBoxing.Backend.Models;
using Microsoft.EntityFrameworkCore;
using System.Text.Json;

namespace CrisCyborgBoxing.Backend.Services;

public interface ITournamentService
{
    Task<Tournament?> CreateTournamentAsync(string name, int maxPlayers, DateTime startTime);
    Task<bool> RegisterPlayerInTournamentAsync(int tournamentId, int playerId);
    Task<Tournament?> GetTournamentAsync(int tournamentId);
    Task<List<Tournament>> GetActiveTournamentsAsync();
    Task GenerateBracketAsync(int tournamentId);
    Task<List<TournamentEntry>> GetTournamentLeaderboardAsync(int tournamentId);
}

public class TournamentService : ITournamentService
{
    private readonly AppDbContext _dbContext;
    private readonly ILogger<TournamentService> _logger;

    public TournamentService(AppDbContext dbContext, ILogger<TournamentService> logger)
    {
        _dbContext = dbContext;
        _logger = logger;
    }

    public async Task<Tournament?> CreateTournamentAsync(string name, int maxPlayers, DateTime startTime)
    {
        try
        {
            var tournament = new Tournament
            {
                Name = name,
                MaxPlayers = maxPlayers,
                StartTime = startTime,
                Status = TournamentStatus.Pending,
                CreatedByAdminId = 1, // Admin ID
                PrizePool = maxPlayers * 10 // 10 tokens per player
            };

            _dbContext.Tournaments.Add(tournament);
            await _dbContext.SaveChangesAsync();

            _logger.LogInformation($"Tournament created: {name} (Max Players: {maxPlayers})");
            return tournament;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error creating tournament: {ex.Message}");
            return null;
        }
    }

    public async Task<bool> RegisterPlayerInTournamentAsync(int tournamentId, int playerId)
    {
        try
        {
            var tournament = await _dbContext.Tournaments
                .Include(t => t.Entries)
                .FirstOrDefaultAsync(t => t.Id == tournamentId);

            if (tournament == null)
            {
                _logger.LogWarning($"Tournament {tournamentId} not found");
                return false;
            }

            if (tournament.Entries.Count >= tournament.MaxPlayers)
            {
                _logger.LogWarning($"Tournament {tournamentId} is full");
                return false;
            }

            // Check if already registered
            if (tournament.Entries.Any(e => e.PlayerId == playerId))
            {
                _logger.LogWarning($"Player {playerId} already registered in tournament {tournamentId}");
                return false;
            }

            var entry = new TournamentEntry
            {
                TournamentId = tournamentId,
                PlayerId = playerId,
                Ranking = tournament.Entries.Count + 1
            };

            _dbContext.TournamentEntries.Add(entry);
            await _dbContext.SaveChangesAsync();

            _logger.LogInformation($"Player {playerId} registered in tournament {tournamentId}");
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error registering player in tournament: {ex.Message}");
            return false;
        }
    }

    public async Task<Tournament?> GetTournamentAsync(int tournamentId)
    {
        return await _dbContext.Tournaments
            .Include(t => t.Entries)
            .ThenInclude(e => e.Player)
            .FirstOrDefaultAsync(t => t.Id == tournamentId);
    }

    public async Task<List<Tournament>> GetActiveTournamentsAsync()
    {
        return await _dbContext.Tournaments
            .Where(t => t.Status == TournamentStatus.Active || t.Status == TournamentStatus.Pending)
            .Include(t => t.Entries)
            .OrderByDescending(t => t.StartTime)
            .ToListAsync();
    }

    public async Task GenerateBracketAsync(int tournamentId)
    {
        try
        {
            var tournament = await _dbContext.Tournaments
                .Include(t => t.Entries)
                .FirstOrDefaultAsync(t => t.Id == tournamentId);

            if (tournament == null)
                return;

            var players = tournament.Entries.Select(e => e.Player).ToList();
            var bracket = GenerateSingleEliminationBracket(players);

            tournament.BracketJson = JsonSerializer.Serialize(bracket);
            tournament.Status = TournamentStatus.Active;

            _dbContext.Update(tournament);
            await _dbContext.SaveChangesAsync();

            _logger.LogInformation($"Bracket generated for tournament {tournamentId}");
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error generating bracket: {ex.Message}");
        }
    }

    public async Task<List<TournamentEntry>> GetTournamentLeaderboardAsync(int tournamentId)
    {
        return await _dbContext.TournamentEntries
            .Where(e => e.TournamentId == tournamentId)
            .Include(e => e.Player)
            .OrderBy(e => e.Ranking)
            .ToListAsync();
    }

    private List<object> GenerateSingleEliminationBracket(List<Player?> players)
    {
        // Simple single elimination bracket generation
        var bracket = new List<object>();
        var playerList = players.Where(p => p != null).ToList();

        for (int i = 0; i < playerList.Count - 1; i += 2)
        {
            bracket.Add(new
            {
                Player1 = playerList[i]?.Username,
                Player2 = i + 1 < playerList.Count ? playerList[i + 1]?.Username : null,
                Round = 1
            });
        }

        return bracket;
    }
}
