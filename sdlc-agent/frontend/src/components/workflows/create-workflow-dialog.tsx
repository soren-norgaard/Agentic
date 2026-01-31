"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { api, Project } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"

interface CreateWorkflowDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
  preselectedProjectId?: string
}

export function CreateWorkflowDialog({
  open,
  onOpenChange,
  onSuccess,
  preselectedProjectId,
}: CreateWorkflowDialogProps) {
  const { toast } = useToast()
  const [isLoading, setIsLoading] = useState(false)
  const [projects, setProjects] = useState<Project[]>([])
  const [loadingProjects, setLoadingProjects] = useState(false)
  const [formData, setFormData] = useState({
    project_id: preselectedProjectId || "",
    name: "",
    description: "",
  })

  useEffect(() => {
    if (open) {
      loadProjects()
    }
  }, [open])

  useEffect(() => {
    if (preselectedProjectId) {
      setFormData(prev => ({ ...prev, project_id: preselectedProjectId }))
    }
  }, [preselectedProjectId])

  // Auto-select first project if only one exists and no project is selected
  useEffect(() => {
    if (projects.length === 1 && !formData.project_id && !preselectedProjectId) {
      setFormData(prev => ({ ...prev, project_id: projects[0].id }))
    }
  }, [projects, formData.project_id, preselectedProjectId])

  const loadProjects = async () => {
    setLoadingProjects(true)
    try {
      const response = await api.projects.list(0, 100)
      setProjects(response.items)
    } catch (error) {
      console.error("Failed to load projects:", error)
    } finally {
      setLoadingProjects(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.project_id) {
      toast({
        title: "Validation Error",
        description: "Please select a project",
        variant: "destructive",
      })
      return
    }

    if (!formData.name.trim()) {
      toast({
        title: "Validation Error",
        description: "Workflow name is required",
        variant: "destructive",
      })
      return
    }

    setIsLoading(true)

    try {
      // Debug: log what we're sending
      const payload = {
        project_id: formData.project_id,
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
      };
      console.log("Creating workflow with payload:", payload);
      
      // Create workflow
      const workflow = await api.workflows.create(payload)

      // Automatically start the workflow
      await api.workflows.action(workflow.id, 'start')

      toast({
        title: "Success",
        description: `Workflow "${workflow.name}" created and started`,
      })

      // Reset form
      setFormData({ project_id: preselectedProjectId || "", name: "", description: "" })
      onOpenChange(false)
      
      if (onSuccess) {
        onSuccess()
      }
    } catch (error: any) {
      console.error("Failed to create workflow:", error)
      // Show detailed error message
      let errorMessage = "Failed to create workflow";
      if (error?.data?.detail) {
        if (Array.isArray(error.data.detail)) {
          errorMessage = error.data.detail.map((d: any) => `${d.loc?.join('.')}: ${d.msg}`).join(', ');
        } else {
          errorMessage = error.data.detail;
        }
      } else if (error?.message) {
        errorMessage = error.message;
      }
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create New Workflow</DialogTitle>
            <DialogDescription>
              Start a new SDLC workflow. Describe what you want to build and the agents
              will help you with requirements, planning, development, testing, and deployment.
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="project">Project *</Label>
              {loadingProjects ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading projects...
                </div>
              ) : (
                <Select
                  value={formData.project_id}
                  onValueChange={(value) => setFormData({ ...formData, project_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a project" />
                  </SelectTrigger>
                  <SelectContent>
                    {projects.map((project) => (
                      <SelectItem key={project.id} value={project.id}>
                        {project.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="name">Workflow Name *</Label>
              <Input
                id="name"
                placeholder="e.g., User Authentication Feature"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                disabled={isLoading}
                required
                minLength={1}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="description">Description / Objective</Label>
              <Textarea
                id="description"
                placeholder="Describe what you want to build. Be specific about features, requirements, and any constraints..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                disabled={isLoading}
                rows={4}
              />
              <p className="text-xs text-muted-foreground">
                This will be used by the AI agents to understand your requirements and plan the work.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create & Start Workflow
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
