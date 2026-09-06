using CrisCyborgBoxing.Backend.Models;
using Microsoft.EntityFrameworkCore;

namespace CrisCyborgBoxing.Backend.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<Player> Players { get; set; }
    public DbSet<Match> Matches { get; set; }
    public DbSet<Tournament> Tournaments { get; set; }
    public DbSet<TournamentEntry> TournamentEntries { get; set; }
    public DbSet<Reward> Rewards { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Player configuration
        modelBuilder.Entity<Player>()
            .HasKey(p => p.Id);
        modelBuilder.Entity<Player>()
            .HasIndex(p => p.MetaMaskAddress)
            .IsUnique();
        modelBuilder.Entity<Player>()
            .HasIndex(p => p.Username)
            .IsUnique();

        // Match configuration
        modelBuilder.Entity<Match>()
            .HasKey(m => m.Id);
        modelBuilder.Entity<Match>()
            .HasOne(m => m.Player1)
            .WithMany(p => p.MatchesAsPlayer1)
            .HasForeignKey(m => m.Player1Id)
            .OnDelete(DeleteBehavior.Restrict);
        modelBuilder.Entity<Match>()
            .HasOne(m => m.Player2)
            .WithMany(p => p.MatchesAsPlayer2)
            .HasForeignKey(m => m.Player2Id)
            .OnDelete(DeleteBehavior.Restrict);
        modelBuilder.Entity<Match>()
            .HasOne(m => m.Winner)
            .WithMany()
            .HasForeignKey(m => m.WinnerId)
            .OnDelete(DeleteBehavior.SetNull);

        // Tournament configuration
        modelBuilder.Entity<Tournament>()
            .HasKey(t => t.Id);
        modelBuilder.Entity<Tournament>()
            .HasMany(t => t.Entries)
            .WithOne(te => te.Tournament)
            .HasForeignKey(te => te.TournamentId);

        // TournamentEntry configuration
        modelBuilder.Entity<TournamentEntry>()
            .HasKey(te => te.Id);
        modelBuilder.Entity<TournamentEntry>()
            .HasOne(te => te.Player)
            .WithMany(p => p.TournamentEntries)
            .HasForeignKey(te => te.PlayerId);

        // Reward configuration
        modelBuilder.Entity<Reward>()
            .HasKey(r => r.Id);
        modelBuilder.Entity<Reward>()
            .HasOne(r => r.Player)
            .WithMany(p => p.Rewards)
            .HasForeignKey(r => r.PlayerId);

        // Seed Cris Cyborg as pre-loaded expert boxer
        modelBuilder.Entity<Player>().HasData(
            new Player
            {
                Id = 1,
                MetaMaskAddress = "0x0000000000000000000000000000000000000000",
                Username = "CrisCyborg",
                SkillLevel = 10,
                Wins = 1000,
                Losses = 0,
                Balance = 50000,
                CreatedAt = DateTime.UtcNow,
                LastLoginAt = DateTime.UtcNow,
                IsActive = true
            }
        );
    }
}
