enum UserRole { user, admin, superAdmin, unknown }
UserRole parseRole(String? r) {
  switch (r) {
    case 'user': return UserRole.user;
    case 'admin': return UserRole.admin;
    case 'super_admin': return UserRole.superAdmin;
    default: return UserRole.unknown;
  }
}
