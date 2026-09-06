using System;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace CrisCyborgBoxing.Backend.Data.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreateModelSnapshot : ModelSnapshot
    {
        protected override void BuildModel(ModelBuilder modelBuilder)
        {
#pragma warning disable 612, 618
            modelBuilder
                .HasAnnotation("ProductVersion", "8.0.0")
                .HasAnnotation("Relational:MaxIdentifierLength", 128);

            SqlServerModelBuilderExtensions.UseIdentityColumns(modelBuilder);

            // Player configuration
            modelBuilder.Entity("CrisCyborgBoxing.Backend.Models.Player", b =>
            {
                b.Property<int>("Id")
                    .ValueGeneratedOnAdd()
                    .HasColumnType("int");

                SqlServerPropertyBuilderExtensions.UseIdentityColumn(b.Property<int>("Id"));

                b.Property<decimal>("Balance")
                    .HasColumnType("decimal(18,2)");

                b.Property<DateTime>("CreatedAt")
                    .HasColumnType("datetime2");

                b.Property<bool>("IsActive")
                    .HasColumnType("bit");

                b.Property<DateTime>("LastLoginAt")
                    .HasColumnType("datetime2");

                b.Property<int>("Losses")
                    .HasColumnType("int");

                b.Property<string>("MetaMaskAddress")
                    .IsRequired()
                    .HasColumnType("nvarchar(450)");

                b.Property<int>("SkillLevel")
                    .HasColumnType("int");

                b.Property<string>("Username")
                    .IsRequired()
                    .HasColumnType("nvarchar(450)");

                b.Property<int>("Wins")
                    .HasColumnType("int");

                b.HasKey("Id");

                b.HasIndex("MetaMaskAddress")
                    .IsUnique();

                b.HasIndex("Username")
                    .IsUnique();

                b.ToTable("Players");

                b.HasData(
                    new
                    {
                        Id = 1,
                        Balance = 50000m,
                        CreatedAt = new DateTime(2026, 6, 7, 16, 31, 5, 809, DateTimeKind.Utc).AddTicks(8379),
                        IsActive = true,
                        LastLoginAt = new DateTime(2026, 6, 7, 16, 31, 5, 809, DateTimeKind.Utc).AddTicks(8379),
                        Losses = 0,
                        MetaMaskAddress = "0x0000000000000000000000000000000000000000",
                        SkillLevel = 10,
                        Username = "CrisCyborg",
                        Wins = 1000
                    });
            });

            // Additional model configurations would go here
#pragma warning restore 612, 618
        }
    }
}
