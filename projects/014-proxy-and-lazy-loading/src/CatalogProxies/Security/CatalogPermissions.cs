namespace CatalogProxies.Security;

[Flags]
public enum CatalogPermissions
{
    None = 0,
    ReadCatalog = 1,
    ViewCost = 2,
    WriteCatalog = 4,
    DeleteCatalog = 8,
}

/// <summary>Who is calling. In a web app this would be built from the request's claims.</summary>
public interface IUserContext
{
    string UserName { get; }

    bool Has(CatalogPermissions permission);
}

/// <summary>A fixed set of permissions, enough for demos, tests and background jobs.</summary>
public sealed record StaticUserContext(string UserName, CatalogPermissions Permissions) : IUserContext
{
    public bool Has(CatalogPermissions permission) => permission != CatalogPermissions.None && Permissions.HasFlag(permission);
}

public sealed class AccessDeniedException : Exception
{
    public AccessDeniedException()
    {
    }

    public AccessDeniedException(string message)
        : base(message)
    {
    }

    public AccessDeniedException(string message, Exception innerException)
        : base(message, innerException)
    {
    }

    public AccessDeniedException(string userName, CatalogPermissions required, string operation)
        : base($"User '{userName}' needs {required} to {operation}.")
    {
        UserName = userName;
        Required = required;
    }

    public string? UserName { get; }

    public CatalogPermissions Required { get; }
}
