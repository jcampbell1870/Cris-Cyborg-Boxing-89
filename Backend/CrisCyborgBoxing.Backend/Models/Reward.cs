namespace CrisCyborgBoxing.Backend.Models;

public class Reward
{
    public int Id { get; set; }
    public int PlayerId { get; set; }
    public decimal Amount { get; set; } // Amount in Arcade1870 (ARC)
    public string? TransactionHash { get; set; }
    public RewardStatus Status { get; set; } = RewardStatus.Pending;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? CompletedAt { get; set; }
    public RewardType RewardType { get; set; }
    public int? MatchId { get; set; }
    public string? ErrorMessage { get; set; }

    // EIP-712 Arcade1870RewardVault claim details. The player submits these
    // values themselves to the vault's claim(...) function - the backend
    // never holds or transfers ARC directly.
    public string? Nonce { get; set; }
    public long? Deadline { get; set; }
    public string? Signature { get; set; }

    public virtual Player? Player { get; set; }
}

public enum RewardStatus
{
    Pending,
    Processing,

    /// <summary>A signed vault claim has been issued to the player but not yet submitted on-chain.</summary>
    Issued,
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
