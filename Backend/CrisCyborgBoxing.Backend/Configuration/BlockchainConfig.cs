namespace CrisCyborgBoxing.Backend.Configuration;

/// <summary>
/// Configuration for the Arcade1870 (ARC) token reward integration.
/// This mirrors the Crypto Chess reward system: rewards are issued as
/// off-chain, EIP-712 signed claims against a shared, pre-funded
/// Arcade1870RewardVault contract rather than being transferred directly by
/// a custodial private key. Players submit the signed claim themselves and
/// pay their own gas, receiving ARC directly in their connected wallet.
/// </summary>
public class BlockchainConfig
{
    public string RpcUrl { get; set; } = string.Empty;

    /// <summary>Arcade1870 (ARC) ERC-20 token contract address.</summary>
    public string TokenAddress { get; set; } = string.Empty;

    /// <summary>
    /// Deployed Arcade1870RewardVault address. This vault is chain- and
    /// consumer-agnostic and is shared as the treasury across multiple
    /// Arcade1870 games (e.g. Crypto Chess and Cris Cyborg Boxing) - do not
    /// deploy a second vault, reuse this same address.
    /// </summary>
    public string RewardVaultAddress { get; set; } = string.Empty;

    /// <summary>
    /// Private key for the dedicated reward signer used to produce EIP-712
    /// claim signatures. This key never has custody of ARC funds - it can
    /// only authorize claims against the vault. Store this in a secrets
    /// manager (e.g. Azure Key Vault) in production, never in source control.
    /// </summary>
    public string RewardSignerPrivateKey { get; set; } = string.Empty;

    public int ChainId { get; set; } = 1;
    public string ChainName { get; set; } = "Ethereum Mainnet";
    public decimal GasPrice { get; set; }
    public long GasLimit { get; set; }

    /// <summary>Default ARC reward amount issued per claim.</summary>
    public decimal RewardAmount { get; set; } = 10;

    /// <summary>ARC token decimals (18 for a standard ERC-20).</summary>
    public int TokenDecimals { get; set; } = 18;

    /// <summary>How long an issued claim signature remains valid, in seconds.</summary>
    public int ClaimTtlSeconds { get; set; } = 600;

    /// <summary>Minimum time a player must wait between reward claims, in milliseconds.</summary>
    public long MinClaimIntervalMs { get; set; } = 60 * 60 * 1000;
}
