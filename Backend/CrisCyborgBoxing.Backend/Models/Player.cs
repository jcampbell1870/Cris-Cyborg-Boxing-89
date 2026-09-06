namespace CrisCyborgBoxing.Backend.Models;

public class Player
{
    public int Id { get; set; }
    public string MetaMaskAddress { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;
    public int SkillLevel { get; set; } // 1-10
    public int Wins { get; set; }
    public int Losses { get; set; }
    public decimal Balance { get; set; } // 1870Coin balance
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime LastLoginAt { get; set; } = DateTime.UtcNow;
    public bool IsActive { get; set; } = true;

    public virtual ICollection<Match> MatchesAsPlayer1 { get; set; } = new List<Match>();
    public virtual ICollection<Match> MatchesAsPlayer2 { get; set; } = new List<Match>();
    public virtual ICollection<TournamentEntry> TournamentEntries { get; set; } = new List<TournamentEntry>();
    public virtual ICollection<Reward> Rewards { get; set; } = new List<Reward>();
}
