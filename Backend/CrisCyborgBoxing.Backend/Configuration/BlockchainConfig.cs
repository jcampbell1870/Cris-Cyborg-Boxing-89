namespace CrisCyborgBoxing.Backend.Configuration;

public class BlockchainConfig
{
    public string RpcUrl { get; set; } = string.Empty;
    public string ContractAddress { get; set; } = string.Empty;
    public string PrivateKey { get; set; } = string.Empty;
    public int ChainId { get; set; }
    public string ChainName { get; set; } = string.Empty;
    public decimal GasPrice { get; set; }
    public long GasLimit { get; set; }
}
