namespace CrisCyborgBoxing.Backend.Models;

public class TournamentEntry
{
    public int Id { get; set; }
    public int TournamentId { get; set; }
    public int PlayerId { get; set; }
    public int Ranking { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTime JoinedAt { get; set; } = DateTime.UtcNow;

    public virtual Tournament? Tournament { get; set; }
    public virtual Player? Player { get; set; }
}
