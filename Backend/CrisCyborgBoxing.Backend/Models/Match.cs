namespace CrisCyborgBoxing.Backend.Models;

public class Match
{
    public int Id { get; set; }
    public int Player1Id { get; set; }
    public int Player2Id { get; set; }
    public int? WinnerId { get; set; }
    public decimal RewardAmount { get; set; }
    public DateTime StartTime { get; set; }
    public DateTime? EndTime { get; set; }
    public MatchState State { get; set; } = MatchState.Pending;
    public int Player1Score { get; set; }
    public int Player2Score { get; set; }
    public int RoundsCompleted { get; set; }
    public string? MatchData { get; set; } // JSON serialized match replay
    public int? TournamentId { get; set; }

    public virtual Player? Player1 { get; set; }
    public virtual Player? Player2 { get; set; }
    public virtual Player? Winner { get; set; }
    public virtual Tournament? Tournament { get; set; }
}

public enum MatchState
{
    Pending,
    InProgress,
    Completed,
    Cancelled
}
