from enum import StrEnum

from app.models.identity import User


class Permission(StrEnum):
    DASHBOARD_READ = "dashboard:read"
    TOURS_READ = "tours:read"
    TOURS_WRITE = "tours:write"
    DEPARTURES_READ = "departures:read"
    DEPARTURES_WRITE = "departures:write"
    BOOKINGS_READ = "bookings:read"
    BOOKINGS_CREATE = "bookings:create"
    BOOKINGS_CREATE_FOR_CUSTOMERS = "bookings:create_for_customers"
    BOOKINGS_WRITE = "bookings:write"
    BOOKINGS_STATUS = "bookings:status"
    CUSTOMERS_READ = "customers:read"
    CUSTOMERS_WRITE = "customers:write"
    ITINERARIES_READ = "itineraries:read"
    ITINERARIES_WRITE = "itineraries:write"
    GUIDES_READ = "guides:read"
    GUIDES_WRITE = "guides:write"
    ASSIGNMENTS_READ = "assignments:read"
    ASSIGNMENTS_WRITE = "assignments:write"
    ARTICLES_READ = "articles:read"
    ARTICLES_WRITE = "articles:write"
    PAYMENTS_READ = "payments:read"
    PAYMENTS_WRITE = "payments:write"
    SUPPLIERS_READ = "suppliers:read"
    SUPPLIERS_WRITE = "suppliers:write"
    EXPENSES_READ = "expenses:read"
    EXPENSES_WRITE = "expenses:write"
    REPORTS_READ = "reports:read"
    USERS_READ = "users:read"
    USERS_MANAGE_STAFF = "users:manage_staff"
    USERS_MANAGE_ADMIN = "users:manage_admin"
    SYSTEM_SETTINGS = "system:settings"


BUSINESS_PERMISSIONS = frozenset(
    {
        Permission.DASHBOARD_READ,
        Permission.TOURS_READ,
        Permission.TOURS_WRITE,
        Permission.DEPARTURES_READ,
        Permission.DEPARTURES_WRITE,
        Permission.BOOKINGS_READ,
        Permission.BOOKINGS_CREATE,
        Permission.BOOKINGS_CREATE_FOR_CUSTOMERS,
        Permission.BOOKINGS_WRITE,
        Permission.BOOKINGS_STATUS,
        Permission.CUSTOMERS_READ,
        Permission.CUSTOMERS_WRITE,
        Permission.ITINERARIES_READ,
        Permission.ITINERARIES_WRITE,
        Permission.GUIDES_READ,
        Permission.GUIDES_WRITE,
        Permission.ASSIGNMENTS_READ,
        Permission.ASSIGNMENTS_WRITE,
        Permission.ARTICLES_READ,
        Permission.ARTICLES_WRITE,
        Permission.PAYMENTS_READ,
        Permission.PAYMENTS_WRITE,
        Permission.SUPPLIERS_READ,
        Permission.SUPPLIERS_WRITE,
        Permission.EXPENSES_READ,
        Permission.EXPENSES_WRITE,
        Permission.REPORTS_READ,
    }
)

ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "SUPER_ADMIN": BUSINESS_PERMISSIONS
    | frozenset(
        {
            Permission.USERS_READ,
            Permission.USERS_MANAGE_STAFF,
            Permission.USERS_MANAGE_ADMIN,
            Permission.SYSTEM_SETTINGS,
        }
    ),
    "ADMIN": BUSINESS_PERMISSIONS
    | frozenset(
        {
            Permission.USERS_READ,
            Permission.USERS_MANAGE_STAFF,
        }
    ),
    "STAFF": frozenset(
        {
            Permission.DASHBOARD_READ,
            Permission.TOURS_READ,
            Permission.DEPARTURES_READ,
            Permission.BOOKINGS_READ,
            Permission.BOOKINGS_CREATE,
            Permission.BOOKINGS_CREATE_FOR_CUSTOMERS,
            Permission.BOOKINGS_WRITE,
            Permission.BOOKINGS_STATUS,
            Permission.CUSTOMERS_READ,
            Permission.CUSTOMERS_WRITE,
            Permission.ITINERARIES_READ,
            Permission.GUIDES_READ,
            Permission.ASSIGNMENTS_READ,
        }
    ),
}


def has_permission(user: User, permission: Permission) -> bool:
    return any(
        permission in ROLE_PERMISSIONS.get(role.code, frozenset())
        for role in user.roles
    )


def assignable_roles(user: User) -> tuple[str, ...]:
    if has_permission(user, Permission.USERS_MANAGE_ADMIN):
        return ("ADMIN", "STAFF", "CUSTOMER")
    if has_permission(user, Permission.USERS_MANAGE_STAFF):
        return ("STAFF", "CUSTOMER")
    return ()
