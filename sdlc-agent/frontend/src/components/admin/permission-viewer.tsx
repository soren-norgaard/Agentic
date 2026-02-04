'use client';

import { useEffect, useState } from 'react';
import { Key, Loader2, RefreshCw, Search, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth-context';

interface Permission {
  id: string;
  code: string;
  name: string;
  description: string | null;
  resource: string;
  action: string;
  scope: string;
  created_at: string;
}

const actionColors: Record<string, string> = {
  create: 'bg-green-500/10 text-green-500 border-green-500/20',
  read: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  update: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  delete: 'bg-red-500/10 text-red-500 border-red-500/20',
};

const scopeColors: Record<string, string> = {
  own: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  any: 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20',
};

export function PermissionViewer() {
  const { tokens } = useAuth();
  const token = tokens?.access_token;
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [resourceFilter, setResourceFilter] = useState<string>('all');
  const [actionFilter, setActionFilter] = useState<string>('all');

  const fetchPermissions = async () => {
    if (!token) return;

    try {
      setLoading(true);
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
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPermissions();
  }, [token]);

  // Get unique resources and actions for filters
  const resources = [...new Set(permissions.map((p) => p.resource))];
  const actions = [...new Set(permissions.map((p) => p.action))];

  // Filter permissions
  const filteredPermissions = permissions.filter((perm) => {
    const matchesSearch =
      searchQuery === '' ||
      perm.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      perm.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      perm.description?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesResource = resourceFilter === 'all' || perm.resource === resourceFilter;
    const matchesAction = actionFilter === 'all' || perm.action === actionFilter;

    return matchesSearch && matchesResource && matchesAction;
  });

  // Group permissions by resource
  const groupedPermissions = filteredPermissions.reduce((acc, perm) => {
    if (!acc[perm.resource]) {
      acc[perm.resource] = [];
    }
    acc[perm.resource].push(perm);
    return acc;
  }, {} as Record<string, Permission[]>);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              Permission Viewer
            </CardTitle>
            <CardDescription>
              View all available permissions in the system
            </CardDescription>
          </div>
          <Button variant="outline" size="icon" onClick={fetchPermissions} disabled={loading}>
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-4">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search permissions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <Select value={resourceFilter} onValueChange={setResourceFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Resource" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Resources</SelectItem>
                {resources.map((resource) => (
                  <SelectItem key={resource} value={resource}>
                    {resource}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={actionFilter} onValueChange={setActionFilter}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Action" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Actions</SelectItem>
                {actions.map((action) => (
                  <SelectItem key={action} value={action}>
                    {action}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="text-sm text-muted-foreground">
            {filteredPermissions.length} of {permissions.length} permissions
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedPermissions).map(([resource, perms]) => (
              <div key={resource}>
                <h3 className="text-sm font-semibold uppercase text-muted-foreground mb-2 flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    {resource}
                  </Badge>
                  <span className="text-xs font-normal">({perms.length} permissions)</span>
                </h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Permission</TableHead>
                      <TableHead>Code</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Scope</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {perms.map((perm) => (
                      <TableRow key={perm.id}>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{perm.name}</span>
                            {perm.description && (
                              <span className="text-sm text-muted-foreground">
                                {perm.description}
                              </span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {perm.code}
                          </code>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={cn("capitalize", actionColors[perm.action])}
                          >
                            {perm.action}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={cn("capitalize", scopeColors[perm.scope])}
                          >
                            {perm.scope}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ))}

            {Object.keys(groupedPermissions).length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                No permissions found matching your filters
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
