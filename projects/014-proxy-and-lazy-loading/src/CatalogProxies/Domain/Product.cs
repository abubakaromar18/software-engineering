namespace CatalogProxies.Domain;

/// <summary>
/// An immutable catalog entry. Immutability matters here: the caching proxy hands the same
/// instance to many callers, so nobody may be able to change it in place.
/// </summary>
public sealed record Product
{
    public Product(ProductId id, string name, string category, decimal price, decimal? costPrice = null)
    {
        if (string.IsNullOrWhiteSpace(name))
        {
            throw new ArgumentException("A product needs a name.", nameof(name));
        }

        if (string.IsNullOrWhiteSpace(category))
        {
            throw new ArgumentException("A product needs a category.", nameof(category));
        }

        ArgumentOutOfRangeException.ThrowIfNegative(price);
        if (costPrice is < 0)
        {
            throw new ArgumentOutOfRangeException(nameof(costPrice), costPrice, "Cost price cannot be negative.");
        }

        Id = id;
        Name = name.Trim();
        Category = category.Trim();
        Price = price;
        CostPrice = costPrice;
    }

    public ProductId Id { get; }

    public string Name { get; }

    /// <summary>Category names are compared case-insensitively.</summary>
    public string Category { get; }

    public decimal Price { get; }

    /// <summary>Commercially sensitive. Only callers with <c>ViewCost</c> may see it.</summary>
    public decimal? CostPrice { get; }

    public Product WithCostPrice(decimal? costPrice) => new(Id, Name, Category, Price, costPrice);
}
