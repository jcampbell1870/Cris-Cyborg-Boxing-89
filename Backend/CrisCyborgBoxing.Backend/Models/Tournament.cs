namespace CrisCyborgBoxing.Backend.Models;

public class Tournament
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public TournamentStatus Status { get; set; } = TournamentStatus.Pending;
    public int MaxPlayers { get; set; }
    public DateTime StartTime { get; set; }
    public DateTime? EndTime { get; set; }
    public string BracketJson { get; set; } = "[]"; // JSON serialized bracket structure
    public decimal PrizePool { get; set; }
    public int CreatedByAdminId { get; set; }

    public virtual ICollection<TournamentEntry> Entries { get; set; } = new List<TournamentEntry>();
}

public enum TournamentStatus
{
    Pending,
    Active,
    Completed,
    Cancelled
}
