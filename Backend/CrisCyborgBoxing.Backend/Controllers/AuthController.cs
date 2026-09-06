using CrisCyborgBoxing.Backend.Models;
using CrisCyborgBoxing.Backend.Services;
using Microsoft.AspNetCore.Mvc;

namespace CrisCyborgBoxing.Backend.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly IAuthenticationService _authService;
    private readonly IMetaMaskService _metaMaskService;
    private readonly ILogger<AuthController> _logger;

    public AuthController(
        IAuthenticationService authService,
        IMetaMaskService metaMaskService,
        ILogger<AuthController> logger)
    {
        _authService = authService;
        _metaMaskService = metaMaskService;
        _logger = logger;
    }

    [HttpGet("message")]
    public IActionResult GetAuthMessage()
    {
        try
        {
            var message = _metaMaskService.GenerateAuthMessage();
            return Ok(new { message });
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error generating auth message: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest request)
    {
        try
        {
            if (request == null || string.IsNullOrEmpty(request.Address) || 
                string.IsNullOrEmpty(request.Signature) || string.IsNullOrEmpty(request.Message))
            {
                return BadRequest(new { error = "Invalid request" });
            }

            var response = await _authService.LoginAsync(request);
            if (!response.Success)
                return Unauthorized(response);

            return Ok(response);
        }
        catch (Exception ex)
        {
            _logger.LogError($"Login error: {ex.Message}");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }
}
