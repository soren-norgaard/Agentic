'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Users, Shield, Key } from 'lucide-react';
import { UserList } from './user-list';
import { UserForm, UserRoleDialog } from './user-form';
import { RoleManagement } from './role-management';
import { PermissionViewer } from './permission-viewer';

interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  status: 'active' | 'inactive' | 'suspended' | 'pending_verification';
  is_superuser: boolean;
  email_verified: boolean;
  last_login_at: string | null;
  created_at: string;
  roles?: Array<{ id: string; name: string }>;
}

export function AdminPanel() {
  const [userFormOpen, setUserFormOpen] = useState(false);
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleCreateUser = () => {
    console.log('handleCreateUser called, setting userFormOpen to true');
    setSelectedUser(null);
    setUserFormOpen(true);
    console.log('userFormOpen state should now be true');
  };

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    setUserFormOpen(true);
  };

  const handleManageRoles = (user: User) => {
    setSelectedUser(user);
    setRoleDialogOpen(true);
  };

  const handleSuccess = () => {
    setRefreshKey((k) => k + 1);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Administration</h1>
        <p className="text-muted-foreground">
          Manage users, roles, and permissions
        </p>
      </div>

      <Tabs defaultValue="users" className="space-y-4">
        <TabsList>
          <TabsTrigger value="users" className="gap-2">
            <Users className="h-4 w-4" />
            Users
          </TabsTrigger>
          <TabsTrigger value="roles" className="gap-2">
            <Shield className="h-4 w-4" />
            Roles
          </TabsTrigger>
          <TabsTrigger value="permissions" className="gap-2">
            <Key className="h-4 w-4" />
            Permissions
          </TabsTrigger>
        </TabsList>

        <TabsContent value="users">
          <UserList
            key={refreshKey}
            onCreateUser={handleCreateUser}
            onEditUser={handleEditUser}
            onManageRoles={handleManageRoles}
          />
        </TabsContent>

        <TabsContent value="roles">
          <RoleManagement />
        </TabsContent>

        <TabsContent value="permissions">
          <PermissionViewer />
        </TabsContent>
      </Tabs>

      {/* User Form Dialog */}
      <UserForm
        open={userFormOpen}
        onOpenChange={setUserFormOpen}
        user={selectedUser}
        onSuccess={handleSuccess}
      />

      {/* User Role Assignment Dialog */}
      <UserRoleDialog
        open={roleDialogOpen}
        onOpenChange={setRoleDialogOpen}
        user={selectedUser}
        onSuccess={handleSuccess}
      />
    </div>
  );
}
