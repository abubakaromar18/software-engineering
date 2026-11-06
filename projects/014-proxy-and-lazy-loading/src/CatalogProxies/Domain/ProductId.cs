namespace CatalogProxies.Domain;

/// <summary>Identifies a product. Normalised to upper case so "sku-1" and "SKU-1" are the same key.</summary>
public readonly record struct ProductId
{
    public ProductId(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new ArgumentException("A product id cannot be empty.", nameof(value));
        }

        Value = value.Trim().ToUpperInvariant();
    }

    public string Value { get; }

    public override string ToString() => Value;
}
