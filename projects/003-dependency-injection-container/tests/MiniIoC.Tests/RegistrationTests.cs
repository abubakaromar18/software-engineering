namespace MiniIoC.Tests;

public class RegistrationTests
{
    [Fact]
    public void Last_registration_wins_for_single_resolution()
    {
        using var container = new ServiceCollection()
            .AddSingleton<IClock, FixedClock>()
            .AddSingleton<IClock, OtherClock>()
            .BuildServiceProvider();

        Assert.IsType<OtherClock>(container.GetRequiredService<IClock>());
    }

    [Fact]
    public void IEnumerable_resolves_all_registrations_in_order()
    {
        using var container = new ServiceCollection()
            .AddSingleton<IClock, FixedClock>()
            .AddTransient<IClock, OtherClock>()
            .BuildServiceProvider();

        var clocks = container.GetServices<IClock>().ToList();

        Assert.Collection(clocks, c => Assert.IsType<FixedClock>(c), c => Assert.IsType<OtherClock>(c));
    }

    [Fact]
    public void Singleton_is_the_same_instance_via_IEnumerable_and_direct_resolution()
    {
        using var container = new ServiceCollection().AddSingleton<IClock, FixedClock>().BuildServiceProvider();

        Assert.Same(container.GetRequiredService<IClock>(), container.GetServices<IClock>().Single());
    }

    [Fact]
    public void IEnumerable_of_an_unregistered_service_is_empty()
    {
        using var container = new ServiceCollection().BuildServiceProvider();

        Assert.Empty(container.GetServices<IClock>());
    }

    [Fact]
    public void Unregistered_service_returns_null_and_required_throws()
    {
        using var container = new ServiceCollection().BuildServiceProvider();

        Assert.Null(container.GetService(typeof(IClock)));
        var ex = Assert.Throws<UnresolvableServiceException>(() => container.GetRequiredService<IClock>());
        Assert.Equal("No service for type 'IClock' has been registered.", ex.Message);
    }

    [Fact]
    public void Instance_registration_returns_the_same_object()
    {
        var clock = new FixedClock();
        using var container = new ServiceCollection().AddSingleton<IClock>(clock).BuildServiceProvider();

        Assert.Same(clock, container.GetRequiredService<IClock>());
    }

    [Fact]
    public void TryAdd_keeps_the_first_registration()
    {
        var services = new ServiceCollection();

        Assert.True(services.TryAdd(ServiceDescriptor.Describe(typeof(IClock), typeof(FixedClock), ServiceLifetime.Singleton)));
        Assert.False(services.TryAdd(ServiceDescriptor.Describe(typeof(IClock), typeof(OtherClock), ServiceLifetime.Singleton)));
        Assert.Single(services);
    }

    [Fact]
    public void Container_is_isolated_from_later_registrations()
    {
        var services = new ServiceCollection();
        using var container = services.BuildServiceProvider();
        services.AddSingleton<IClock, FixedClock>();

        Assert.Null(container.GetService(typeof(IClock)));
    }

    [Theory]
    [InlineData(typeof(IClock), typeof(UnitOfWork))]      // not assignable
    [InlineData(typeof(IClock), typeof(IClock))]          // not concrete
    [InlineData(typeof(IRepository<>), typeof(UnitOfWork))] // open vs closed
    [InlineData(typeof(IRepository<>), typeof(List<>))]   // does not implement
    public void Invalid_descriptors_are_rejected_at_registration(Type service, Type implementation)
    {
        Assert.Throws<ArgumentException>(
            () => ServiceDescriptor.Describe(service, implementation, ServiceLifetime.Transient));
    }

    [Fact]
    public void Instance_must_match_service_type()
    {
        Assert.Throws<ArgumentException>(() => ServiceDescriptor.FromInstance(typeof(IClock), new UnitOfWork()));
    }

    [Fact]
    public void Descriptor_describes_itself()
    {
        var descriptor = ServiceDescriptor.Describe(typeof(IRepository<>), typeof(Repository<>), ServiceLifetime.Scoped);

        Assert.Equal("IRepository<> -> Repository<> (Scoped)", descriptor.ToString());
    }
}
