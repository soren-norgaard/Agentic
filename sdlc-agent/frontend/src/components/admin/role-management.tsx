'use client';

import { useEffect, useState } from 'react';
import {
  Shield,
  Plus,
  MoreHorizontal,
  Edit,
  Trash2,
  Key,
  Loader2,
  RefreshCw,
  Lock,
  Users,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth-context';

interface Role {
  id: string;
  name: string;
  description: string | null;
  role_type: 'system' | 'custom';
  priority: number;
  is_active: boolean;
  created_at: string;
  permissions?: Array<{ id: string; code: string; name: string }>;
}

interface Permission {
  id: string;
  code: string;
  name: string;
  description: string | null;
  resource: string;
  action: string;
  scope: string;
}

export function RoleManagement() {
  const { tokens } = useAuth();
  const token = tokens?.access_token;
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [permDialogOpen, setPermDialogOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [rolePermissions, setRolePermissions] = useState<string[]>([]);

  const fetchRoles = async () => {
    if (!token) return;

    try {
      setLoading(true);
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/roles`,
        {
          headers: { 'Authorization': `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setRoles(data.items || data || []);
      }
    } catch (error) {
      console.error('Failed to fetch roles:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchPermissions = async () => {
    if (!token) return;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/permissions`,
        {
          headers: { 'Authorization': `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setPermissions(data.items || data || []);
      }
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
    }
  };

  useEffect(() => {
    fetchRoles();
    fetchPermissions();
  }, [token]);

  const handleDeleteRole = async (roleId: string) => {
    if (!token || !confirm('Are you sure you want to delete this role?')) return;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/roles/${roleId}`,
        {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` },
        }
      );

      if (response.ok) {
        fetchRoles();
      }
    } catch (error) {
      console.error('Failed to delete role:', error);
    }
  };

  const handleEditRole = (role: Role) => {
    setEditingRole(role);
    setDialogOpen(true);
  };

  const handleCreateRole = () => {
    setEditingRole(null);
    setDialogOpen(true);
  };

  const handleManagePermissions = async (role: Role) => {
    setSelectedRole(role);

    // Fetch role's current permissions
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/roles/${role.id}/permissions`,
        {
          headers: { 'Authorization': `Bearer ${token}` },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setRolePermissions(data.map((p: { permission_id: string }) => p.permission_id));
      }
    } catch (error) {
      console.error('Failed to fetch role permissions:', error);
    }

    setPermDialogOpen(true);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Role Management
            </CardTitle>
            <CardDescription>
              Create and manage roles for access control
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={fetchRoles} disabled={loading}>
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            </Button>
            <Button onClick={handleCreateRole}>
              <Plus className="h-4 w-4 mr-2" />
              Add Role
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Role</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {roles.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No roles found
                  </TableCell>
                </TableRow>
              ) : (
                roles.map((role) => (
                  <TableRow key={role.id}>
                    <TableCell>
                      <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{role.name}</span>
                          {role.role_type === 'system' && (
                            <Lock className="h-3 w-3 text-muted-foreground" />
                          )}
                        </div>
                        {role.description && (
                          <span className="text-sm text-muted-foreground">{role.description}</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={role.role_type === 'system' ? 'default' : 'secondary'}>
                        {role.role_type}
                      </Badge>
                    </TableCell>
                    <TableCell>{role.priority}</TableCell>
                    <TableCell>
                      <Badge variant={role.is_active ? 'default' : 'secondary'}>
                        {role.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(role.created_at)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEditRole(role)}>
                            <Edit className="h-4 w-4 mr-2" />
                            Edit Role
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleManagePermissions(role)}>
                            <Key className="h-4 w-4 mr-2" />
                            Manage Permissions
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => handleDeleteRole(role.id)}
                            disabled={role.role_type === 'system'}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete Role
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {/* Role Form Dialog */}
      <RoleFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        role={editingRole}
        onSuccess={fetchRoles}
      />

      {/* Permissions Dialog */}
      <RolePermissionsDialog
        open={permDialogOpen}
        onOpenChange={setPermDialogOpen}
        role={selectedRole}
        permissions={permissions}
        rolePermissions={rolePermissions}
        setRolePermissions={setRolePermissions}
        onSuccess={fetchRoles}
      />
    </Card>
  );
}

interface RoleFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role?: Role | null;
  onSuccess?: () => void;
}

function RoleFormDialog({ open, onOpenChange, role, onSuccess }: RoleFormDialogProps) {
  const { tokens } = useAuth();
  const token = tokens?.access_token;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    priority: 0,
  });

  const isEditing = !!role;

  useEffect(() => {
    if (role) {
      setFormData({
        name: role.name,
        description: role.description || '',
        priority: role.priority,
      });
    } else {
      setFormData({ name: '', description: '', priority: 0 });
    }
    setError(null);
  }, [role, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    setLoading(true);
    setError(null);

    try {
      const url = isEditing
        ? `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/roles/${role.id}`
        : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/roles`;

      const response = await fetch(url, {
        method: isEditing ? 'PATCH' : 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to save role');
      }

      onSuccess?.();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Role' : 'Create Role'}</DialogTitle>
          <DialogDescription>
            {isEditing ? 'Update role details' : 'Create a new role for access control'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="grid gap-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Role name"
                required
                disabled={isEditing && role?.role_type === 'system'}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Role description"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="priority">Priority (0-100)</Label>
              <Input
                id="priority"
                type="number"
                min={0}
                max={100}
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
              />
              <p className="text-xs text-muted-foreground">
                Higher priority roles take precedence in permission conflicts
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {isEditing ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface RolePermissionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role: Role | null;
  permissions: Permission[];
  rolePermissions: string[];
  setRolePermissions: (perms: string[]) => void;
  onSuccess?: () => void;
}

function RolePermissionsDialog({
  open,
  onOpenChange,
  role,
  permissions,
  rolePermissions,
  setRolePermissions,
  onSuccess,
}: RolePermissionsDialogProps) {
  const { tokens } = useAuth();
  const token = tokens?.access_token;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');

  const groupedPermissions = permissions.reduce((acc, perm) => {
    if (!acc[perm.resource]) {
      acc[perm.resource] = [];
    }
    acc[perm.resource].push(perm);
    return acc;
  }, {} as Record<string, Permission[]>);

  const togglePermission = async (permissionId: string) => {
    if (!role || !token) return;

    setLoading(true);
    setError(null);

    try {
      const hasPermission = rolePermissions.includes(permissionId);
      const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/roles/${role.id}/permissions${hasPermission ? `/${permissionId}` : ''}`;

      const response = await fetch(url, {
        method: hasPermission ? 'DELETE' : 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        ...(hasPermission ? {} : { body: JSON.stringify({ permission_id: permissionId }) }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to update permission');
      }

      if (hasPermission) {
        setRolePermissions(rolePermissions.filter((p) => p !== permissionId));
      } else {
        setRolePermissions([...rolePermissions, permissionId]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    onSuccess?.();
    onOpenChange(false);
  };

  const filteredGroups = Object.entries(groupedPermissions).filter(([resource, perms]) =>
    resource.toLowerCase().includes(filter.toLowerCase()) ||
    perms.some((p) => p.name.toLowerCase().includes(filter.toLowerCase()))
  );

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Manage Permissions</DialogTitle>
          <DialogDescription>
            {role ? `Configure permissions for ${role.name}` : 'Select a role first'}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Input
            placeholder="Filter permissions..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="mb-4"
          />

          <div className="max-h-96 overflow-y-auto space-y-4">
            {filteredGroups.map(([resource, perms]) => (
              <div key={resource}>
                <h4 className="font-medium text-sm uppercase text-muted-foreground mb-2">
                  {resource}
                </h4>
                <div className="space-y-1">
                  {perms.map((perm) => (
                    <div
                      key={perm.id}
                      className="flex items-center justify-between p-2 border rounded hover:bg-muted/50 cursor-pointer"
                      onClick={() => togglePermission(perm.id)}
                    >
                      <div>
                        <div className="text-sm font-medium">{perm.name}</div>
                        <div className="text-xs text-muted-foreground">{perm.code}</div>
                      </div>
                      <input
                        type="checkbox"
                        checked={rolePermissions.includes(perm.id)}
                        onChange={() => {}}
                        disabled={loading}
                        className="h-4 w-4"
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleClose}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
