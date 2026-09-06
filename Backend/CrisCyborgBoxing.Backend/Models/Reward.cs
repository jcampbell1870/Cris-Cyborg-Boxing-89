namespace CrisCyborgBoxing.Backend.Models;

public class Reward
{
    public int Id { get; set; }
    public int PlayerId { get; set; }
    public decimal Amount { get; set; } // Amount in 1870Coin
    public string? TransactionHash { get; set; }
    public RewardStatus Status { get; set; } = RewardStatus.Pending;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? CompletedAt { get; set; }
    public RewardType RewardType { get; set; }
    public int? MatchId { get; set; }
    public string? ErrorMessage { get; set; }

    public virtual Player? Player { get; set; }
}

public enum RewardStatus
{
    Pending,
    Processing,
    Completed,
    Failed
}

public enum RewardType
{
    MatchWin,
    TournamentVictory,
    DailyBonus,
    ReferralBonus
}
