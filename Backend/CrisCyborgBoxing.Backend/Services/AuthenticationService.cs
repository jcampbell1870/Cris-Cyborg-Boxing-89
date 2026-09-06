using CrisCyborgBoxing.Backend.Data;
using CrisCyborgBoxing.Backend.Models;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using Microsoft.IdentityModel.Tokens;
using System.Text;

namespace CrisCyborgBoxing.Backend.Services;

public interface IAuthenticationService
{
    Task<LoginResponse> LoginAsync(LoginRequest request);
    Task<Player?> RegisterPlayerAsync(string metaMaskAddress, string username);
    string GenerateJwtToken(Player player);
    ClaimsPrincipal? ValidateJwtToken(string token);
}

public class AuthenticationService : IAuthenticationService
{
    private readonly AppDbContext _dbContext;
    private readonly IMetaMaskService _metaMaskService;
    private readonly IConfiguration _configuration;
    private readonly ILogger<AuthenticationService> _logger;

    public AuthenticationService(
        AppDbContext dbContext,
        IMetaMaskService metaMaskService,
        IConfiguration configuration,
        ILogger<AuthenticationService> logger)
    {
        _dbContext = dbContext;
        _metaMaskService = metaMaskService;
        _configuration = configuration;
        _logger = logger;
    }

    public async Task<LoginResponse> LoginAsync(LoginRequest request)
    {
        try
        {
            // Verify MetaMask signature
            var isValidSignature = await _metaMaskService.VerifySignatureAsync(
                request.Address,
                request.Message,
                request.Signature);

            if (!isValidSignature)
            {
                return new LoginResponse
                {
                    Success = false,
                    Error = "Invalid signature"
                };
            }

            // Check if player exists
            var player = _dbContext.Players.FirstOrDefault(p => p.MetaMaskAddress == request.Address);

            if (player == null)
            {
                // Auto-create player on first login
                player = await RegisterPlayerAsync(request.Address, $"Player_{request.Address[^6..]}");
            }

            player.LastLoginAt = DateTime.UtcNow;
            _dbContext.Update(player);
            await _dbContext.SaveChangesAsync();

            var token = GenerateJwtToken(player);

            return new LoginResponse
            {
                Success = true,
                Token = token,
                Player = new PlayerDto
                {
                    Id = player.Id,
                    MetaMaskAddress = player.MetaMaskAddress,
                    Username = player.Username,
                    SkillLevel = player.SkillLevel,
                    Wins = player.Wins,
                    Losses = player.Losses,
                    Balance = player.Balance
                }
            };
        }
        catch (Exception ex)
        {
            _logger.LogError($"Login error: {ex.Message}");
            return new LoginResponse
            {
                Success = false,
                Error = "An error occurred during login"
            };
        }
    }

    public async Task<Player?> RegisterPlayerAsync(string metaMaskAddress, string username)
    {
        try
        {
            var existingPlayer = _dbContext.Players
                .FirstOrDefault(p => p.MetaMaskAddress == metaMaskAddress);

            if (existingPlayer != null)
                return existingPlayer;

            var player = new Player
            {
                MetaMaskAddress = metaMaskAddress,
                Username = username,
                SkillLevel = 1,
                Wins = 0,
                Losses = 0,
                Balance = 1, // Start with 1 coin daily bonus
                CreatedAt = DateTime.UtcNow,
                IsActive = true
            };

            _dbContext.Players.Add(player);
            await _dbContext.SaveChangesAsync();

            _logger.LogInformation($"New player registered: {username} ({metaMaskAddress})");
            return player;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Registration error: {ex.Message}");
            return null;
        }
    }

    public string GenerateJwtToken(Player player)
    {
        var jwtSettings = _configuration.GetSection("JwtSettings");
        var secretKey = jwtSettings["SecretKey"] ?? throw new InvalidOperationException("JWT secret key not configured");
        var issuer = jwtSettings["Issuer"] ?? "CrisCyborgBoxing";
        var audience = jwtSettings["Audience"] ?? "CrisCyborgBoxingClients";
        var expiryMinutes = int.Parse(jwtSettings["ExpiryMinutes"] ?? "1440");

        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secretKey));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, player.Id.ToString()),
            new Claim(ClaimTypes.Name, player.Username),
            new Claim("MetaMaskAddress", player.MetaMaskAddress)
        };

        var token = new JwtSecurityToken(
            issuer: issuer,
            audience: audience,
            claims: claims,
            expires: DateTime.UtcNow.AddMinutes(expiryMinutes),
            signingCredentials: creds);

        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    public ClaimsPrincipal? ValidateJwtToken(string token)
    {
        try
        {
            var jwtSettings = _configuration.GetSection("JwtSettings");
            var secretKey = jwtSettings["SecretKey"] ?? throw new InvalidOperationException("JWT secret key not configured");
            var issuer = jwtSettings["Issuer"] ?? "CrisCyborgBoxing";
            var audience = jwtSettings["Audience"] ?? "CrisCyborgBoxingClients";

            var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secretKey));
            var tokenHandler = new JwtSecurityTokenHandler();

            var principal = tokenHandler.ValidateToken(token, new TokenValidationParameters
            {
                ValidateIssuerSigningKey = true,
                IssuerSigningKey = key,
                ValidateIssuer = true,
                ValidIssuer = issuer,
                ValidateAudience = true,
                ValidAudience = audience,
                ValidateLifetime = true,
                ClockSkew = TimeSpan.Zero
            }, out SecurityToken validatedToken);

            return principal;
        }
        catch
        {
            return null;
        }
    }
}
