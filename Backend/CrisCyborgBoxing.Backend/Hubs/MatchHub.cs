using CrisCyborgBoxing.Backend.Data;
using CrisCyborgBoxing.Backend.Models;
using CrisCyborgBoxing.Backend.Services;
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;

namespace CrisCyborgBoxing.Backend.Hubs;

public class MatchHub : Hub
{
    private readonly AppDbContext _dbContext;
    private readonly IRewardService _rewardService;
    private readonly ILogger<MatchHub> _logger;

    public MatchHub(AppDbContext dbContext, IRewardService rewardService, ILogger<MatchHub> logger)
    {
        _dbContext = dbContext;
        _rewardService = rewardService;
        _logger = logger;
    }

    public async Task JoinMatch(int matchId, int playerId)
    {
        try
        {
            await Groups.AddToGroupAsync(Context.ConnectionId, $"match_{matchId}");
            await Clients.Group($"match_{matchId}").SendAsync("PlayerJoined", playerId);
            _logger.LogInformation($"Player {playerId} joined match {matchId}");
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error joining match: {ex.Message}");
        }
    }

    public async Task SendInput(int matchId, int playerId, string inputData)
    {
        try
        {
            // Broadcast input to other player in real-time
            await Clients.Group($"match_{matchId}").SendAsync("ReceiveInput", playerId, inputData);
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error sending input: {ex.Message}");
        }
    }

    public async Task UpdateMatchState(int matchId, string matchState)
    {
        try
        {
            var match = await _dbContext.Matches.FindAsync(matchId);
            if (match != null)
            {
                match.MatchData = matchState;
                _dbContext.Update(match);
                await _dbContext.SaveChangesAsync();
            }

            // Broadcast updated state to both players
            await Clients.Group($"match_{matchId}").SendAsync("MatchStateUpdated", matchState);
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error updating match state: {ex.Message}");
        }
    }

    public async Task EndMatch(int matchId, int winnerId, decimal rewardAmount)
    {
        try
        {
            var match = await _dbContext.Matches.Include(m => m.Player1).Include(m => m.Player2).FirstOrDefaultAsync(m => m.Id == matchId);
            if (match == null)
                return;

            match.WinnerId = winnerId;
            match.RewardAmount = rewardAmount;
            match.EndTime = DateTime.UtcNow;
            match.State = MatchState.Completed;

            _dbContext.Update(match);
            await _dbContext.SaveChangesAsync();

            // Distribute reward
            var reward = await _rewardService.DistributeRewardAsync(winnerId, rewardAmount, RewardType.MatchWin, matchId);

            // Update player wins/losses
            if (match.Player1 != null && match.Player2 != null)
            {
                if (winnerId == match.Player1Id)
                {
                    match.Player1.Wins++;
                    match.Player2.Losses++;
                }
                else
                {
                    match.Player1.Losses++;
                    match.Player2.Wins++;
                }

                _dbContext.Update(match.Player1);
                _dbContext.Update(match.Player2);
                await _dbContext.SaveChangesAsync();
            }

            // Notify both players
            await Clients.Group($"match_{matchId}").SendAsync("MatchEnded", winnerId, rewardAmount);
            _logger.LogInformation($"Match {matchId} ended. Winner: {winnerId}, Reward: {rewardAmount}");
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error ending match: {ex.Message}");
        }
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        _logger.LogWarning($"Client disconnected: {Context.ConnectionId}");
        await base.OnDisconnectedAsync(exception);
    }
}
