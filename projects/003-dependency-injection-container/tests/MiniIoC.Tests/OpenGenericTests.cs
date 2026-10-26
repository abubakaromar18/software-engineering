namespace MiniIoC.Tests;

public class OpenGenericTests
{
    [Fact]
    public void Closes_open_generic_registrations_on_demand()
    {
        using var container = new ServiceCollection()
            .Add(typeof(IRepository<>), typeof(Repository<>), ServiceLifetime.Transient)
            .BuildServiceProvider();

        var users = container.GetRequiredService<IRepository<User>>();

        Assert.IsType<Repository<User>>(users);
        Assert.Equal(typeof(User), users.EntityType);
    }

    [Fact]
    public void Open_generic_singletons_are_per_closed_type()
    {
        using var container = new ServiceCollection()
            .Add(typeof(IRepository<>), typeof(Repository<>), ServiceLifetime.Singleton)
            .BuildServiceProvider();

        var users = container.GetRequiredService<IRepository<User>>();

        Assert.Same(users, container.GetRequiredService<IRepository<User>>());
        Assert.NotSame((object)users, container.GetRequiredService<IRepository<Order>>());
    }

    [Fact]
    public void Closed_registration_takes_precedence_over_open()
    {
        using var container = new ServiceCollection()
            .Add(typeof(IRepository<>), typeof(Repository<>), ServiceLifetime.Transient)
            .AddTransient<IRepository<User>, CachedRepository<User>>()
            .BuildServiceProvider();

        Assert.IsType<CachedRepository<User>>(container.GetRequiredService<IRepository<User>>());
        Assert.IsType<Repository<Order>>(container.GetRequiredService<IRepository<Order>>());
    }

    [Fact]
    public void Open_generics_are_injected_into_constructors()
    {
        using var container = new ServiceCollection()
            .Add(typeof(IRepository<>), typeof(Repository<>), ServiceLifetime.Scoped)
            .AddScoped<UserService>()
            .BuildServiceProvider();
        using var scope = container.CreateScope();

        var service = scope.ServiceProvider.GetRequiredService<UserService>();

        Assert.Same(service.Users, scope.ServiceProvider.GetRequiredService<IRepository<User>>());
    }

    [Fact]
    public void Registrations_whose_constraints_fail_are_skipped()
    {
        using var container = new ServiceCollection()
            .Add(typeof(IRepository<>), typeof(Repository<>), ServiceLifetime.Transient)
            .Add(typeof(IRepository<>), typeof(ValueOnlyRepository<>), ServiceLifetime.Transient)
            .BuildServiceProvider();

        // ValueOnlyRepository<T> requires a struct, so for a class the earlier registration wins...
        Assert.IsType<Repository<User>>(container.GetRequiredService<IRepository<User>>());
        // ...while for a struct the last registration wins as usual.
        Assert.IsType<ValueOnlyRepository<int>>(container.GetRequiredService<IRepository<int>>());
        // IEnumerable includes only the registrations that can be closed.
        Assert.Single(container.GetServices<IRepository<User>>());
        Assert.Equal(2, container.GetServices<IRepository<int>>().Count());
    }

    [Fact]
    public void IEnumerable_mixes_closed_and_open_registrations_in_registration_order()
    {
        using var container = new ServiceCollection()
            .Add(typeof(IRepository<>), typeof(Repository<>), ServiceLifetime.Transient)
            .AddTransient<IRepository<User>, CachedRepository<User>>()
            .BuildServiceProvider();

        Assert.Collection(
            container.GetServices<IRepository<User>>(),
            r => Assert.IsType<Repository<User>>(r),
            r => Assert.IsType<CachedRepository<User>>(r));
    }
}
