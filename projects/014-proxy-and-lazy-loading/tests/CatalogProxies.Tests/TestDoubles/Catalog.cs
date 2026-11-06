using CatalogProxies.Domain;
using CatalogProxies.Security;

namespace CatalogProxies.Tests.TestDoubles;

/// <summary>Shared sample data and users.</summary>
public static class Catalog
{
    public static readonly ProductId KeyboardId = new("KB-100");
    public static readonly ProductId MouseId = new("MS-200");
    public static readonly ProductId DeskId = new("DK-300");
    public static readonly ProductId MissingId = new("NOPE-0");

    public static Product Keyboard { get; } = new(KeyboardId, "Mechanical keyboard", "Peripherals", 129m, 61m);

    public static Product Mouse { get; } = new(MouseId, "Wireless mouse", "Peripherals", 49m, 18m);

    public static Product Desk { get; } = new(DeskId, "Standing desk", "Furniture", 599m, 310m);

    public static Product[] All => [Keyboard, Mouse, Desk];

    public static IUserContext Anonymous { get; } = new StaticUserContext("anonymous", CatalogPermissions.None);

    public static IUserContext Shopper { get; } = new StaticUserContext("shopper", CatalogPermissions.ReadCatalog);

    public static IUserContext Merchandiser { get; } =
        new StaticUserContext("merch", CatalogPermissions.ReadCatalog | CatalogPermissions.WriteCatalog);

    public static IUserContext Admin { get; } = new StaticUserContext(
        "admin",
        CatalogPermissions.ReadCatalog | CatalogPermissions.ViewCost | CatalogPermissions.WriteCatalog | CatalogPermissions.DeleteCatalog);
}
