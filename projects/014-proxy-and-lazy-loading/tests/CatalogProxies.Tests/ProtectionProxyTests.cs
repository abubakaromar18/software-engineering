using CatalogProxies.Domain;
using CatalogProxies.Proxies;
using CatalogProxies.Security;
using CatalogProxies.Tests.TestDoubles;

namespace CatalogProxies.Tests;

public class ProtectionProxyTests
{
    private readonly SpyRepository _store = new(Catalog.All);

    [Theory]
    [InlineData("get")]
    [InlineData("list")]
    [InlineData("save")]
    [InlineData("delete")]
    public async Task A_user_without_permissions_is_denied_before_the_store_is_touched(string operation)
    {
        var repo = new ProtectionRepositoryProxy(_store, Catalog.Anonymous);

        Func<Task> call = operation switch
        {
            "get" => () => repo.GetByIdAsync(Catalog.KeyboardId),
            "list" => () => repo.ListByCategoryAsync("Peripherals"),
            "save" => () => repo.SaveAsync(Catalog.Desk),
            _ => () => repo.DeleteAsync(Catalog.DeskId),
        };

        var denied = await Assert.ThrowsAsync<AccessDeniedException>(call);
        Assert.Equal("anonymous", denied.UserName);
        Assert.Equal(0, _store.TotalCalls);
    }

    [Fact]
    public async Task Readers_see_products_without_the_cost_price()
    {
        var repo = new ProtectionRepositoryProxy(_store, Catalog.Shopper);

        var keyboard = await repo.GetByIdAsync(Catalog.KeyboardId);
        var peripherals = await repo.ListByCategoryAsync("Peripherals");

        Assert.NotNull(keyboard);
        Assert.Equal(129m, keyboard!.Price);
        Assert.Null(keyboard.CostPrice);
        Assert.All(peripherals, p => Assert.Null(p.CostPrice));
    }

    [Fact]
    public async Task Users_with_ViewCost_see_the_cost_price()
    {
        var repo = new ProtectionRepositoryProxy(_store, Catalog.Admin);

        var keyboard = await repo.GetByIdAsync(Catalog.KeyboardId);

        Assert.Equal(61m, keyboard!.CostPrice);
    }

    [Fact]
    public async Task Missing_products_come_back_as_null_rather_than_denied()
    {
        var repo = new ProtectionRepositoryProxy(_store, Catalog.Shopper);

        Assert.Null(await repo.GetByIdAsync(Catalog.MissingId));
    }

    [Fact]
    public async Task Readers_cannot_write_or_delete()
    {
        var repo = new ProtectionRepositoryProxy(_store, Catalog.Shopper);

        var save = await Assert.ThrowsAsync<AccessDeniedException>(() => repo.SaveAsync(Catalog.Desk));
        var delete = await Assert.ThrowsAsync<AccessDeniedException>(() => repo.DeleteAsync(Catalog.DeskId));

        Assert.Equal(CatalogPermissions.WriteCatalog, save.Required);
        Assert.Equal(CatalogPermissions.DeleteCatalog, delete.Required);
        Assert.Contains("shopper", save.Message);
    }

    [Fact]
    public async Task A_writer_who_cannot_see_costs_keeps_the_stored_cost_price()
    {
        var repo = new ProtectionRepositoryProxy(_store, Catalog.Merchandiser);

        // The merchandiser read a redacted keyboard, changed the price and saved it back.
        var redacted = (await repo.GetByIdAsync(Catalog.KeyboardId))!;
        var repriced = new Product(redacted.Id, redacted.Name, redacted.Category, 119m, redacted.CostPrice);
        await repo.SaveAsync(repriced);

        var stored = _store.Stored(Catalog.KeyboardId)!;
        Assert.Equal(119m, stored.Price);
        Assert.Equal(61m, stored.CostPrice);
    }

    [Fact]
    public async Task A_writer_who_cannot_see_costs_cannot_set_one_either()
    {
        var repo = new ProtectionRepositoryProxy(_store, Catalog.Merchandiser);

        await repo.SaveAsync(new Product(new ProductId("LMP-1"), "Desk lamp", "Furniture", 39m, costPrice: 1m));

        Assert.Null(_store.Stored(new ProductId("lmp-1"))!.CostPrice);
    }

    [Fact]
    public async Task An_admin_can_change_the_cost_price_and_delete()
    {
        var repo = new ProtectionRepositoryProxy(_store, Catalog.Admin);

        await repo.SaveAsync(Catalog.Mouse.WithCostPrice(20m));
        Assert.Equal(20m, _store.Stored(Catalog.MouseId)!.CostPrice);

        Assert.True(await repo.DeleteAsync(Catalog.MouseId));
        Assert.Null(_store.Stored(Catalog.MouseId));
    }

    [Fact]
    public void The_None_permission_is_never_granted()
    {
        var everything = new StaticUserContext("root", (CatalogPermissions)0xFF);

        Assert.False(everything.Has(CatalogPermissions.None));
        Assert.True(everything.Has(CatalogPermissions.ViewCost));
    }
}
