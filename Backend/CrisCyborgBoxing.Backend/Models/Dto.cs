namespace CrisCyborgBoxing.Backend.Models;

public class MetaMaskAuth
{
    public string Address { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public string Signature { get; set; } = string.Empty;
}

public class LoginRequest
{
    public string Address { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public string Signature { get; set; } = string.Empty;
}

public class LoginResponse
{
    public bool Success { get; set; }
    public string? Token { get; set; }
    public PlayerDto? Player { get; set; }
    public string? Error { get; set; }
}

public class PlayerDto
{
    public int Id { get; set; }
    public string MetaMaskAddress { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;
    public int SkillLevel { get; set; }
    public int Wins { get; set; }
    public int Losses { get; set; }
    public decimal Balance { get; set; }
}
