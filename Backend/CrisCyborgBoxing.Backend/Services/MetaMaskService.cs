using CrisCyborgBoxing.Backend.Configuration;
using CrisCyborgBoxing.Backend.Models;
using Nethereum.Signer;

namespace CrisCyborgBoxing.Backend.Services;

public interface IMetaMaskService
{
    Task<bool> VerifySignatureAsync(string address, string message, string signature);
    string GenerateAuthMessage();
    Task<bool> ValidateWalletAsync(string address);
}

public class MetaMaskService : IMetaMaskService
{
    private readonly ILogger<MetaMaskService> _logger;

    public MetaMaskService(ILogger<MetaMaskService> logger)
    {
        _logger = logger;
    }

    public string GenerateAuthMessage()
    {
        return $"Welcome to Cris Cyborg Boxing!\n\n" +
               $"Please sign this message to verify your wallet.\n\n" +
               $"Timestamp: {DateTime.UtcNow:O}";
    }

    public async Task<bool> VerifySignatureAsync(string address, string message, string signature)
    {
        try
        {
            if (string.IsNullOrEmpty(address) || string.IsNullOrEmpty(message) || string.IsNullOrEmpty(signature))
            {
                _logger.LogWarning("Invalid signature parameters provided");
                return false;
            }

            var signer = new EthereumMessageSigner();
            var recoveredAddress = signer.EncodeUTF8AndEcRecover(message, signature);

            var isValid = recoveredAddress.Equals(address, StringComparison.OrdinalIgnoreCase);

            if (!isValid)
            {
                _logger.LogWarning($"Signature verification failed for address: {address}");
            }

            return isValid;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error verifying signature: {ex.Message}");
            return false;
        }
    }

    public async Task<bool> ValidateWalletAsync(string address)
    {
        try
        {
            if (string.IsNullOrEmpty(address))
                return false;

            // Basic address validation (0x followed by 40 hex characters)
            return address.StartsWith("0x") && address.Length == 42;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error validating wallet: {ex.Message}");
            return false;
        }
    }
}
