'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  Sparkles,
  Brain,
  GitBranch,
  Shield,
  Rocket,
  Users,
  Target,
  Palette,
  Code,
  CheckCircle2,
  Zap,
  BarChart3,
  FileText,
  Layers,
  Bot,
  CircleDot,
  Play,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface LandingPageProps {
  onGetStarted: () => void;
}

// Workflow step component
function WorkflowStep({ 
  icon: Icon, 
  title, 
  description, 
  color,
  agent,
  isActive,
  delay 
}: { 
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  color: string;
  agent: string;
  isActive?: boolean;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      viewport={{ once: true }}
      className="relative"
    >
      <div className={cn(
        "relative z-10 flex flex-col items-center text-center p-6 rounded-2xl border bg-card transition-all duration-300",
        isActive && "ring-2 ring-primary shadow-lg"
      )}>
        <div className={cn(
          "w-16 h-16 rounded-2xl flex items-center justify-center mb-4",
          color
        )}>
          <Icon className="w-8 h-8 text-white" />
        </div>
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-sm text-muted-foreground mb-3">{description}</p>
        <div className="flex items-center gap-2 text-xs font-medium">
          <Bot className="w-3.5 h-3.5" />
          <span>{agent}</span>
        </div>
      </div>
    </motion.div>
  );
}

// Role card component
function RoleCard({
  icon: Icon,
  title,
  benefits,
  color,
  delay,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  benefits: string[];
  color: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      viewport={{ once: true }}
    >
      <Card className="h-full hover:shadow-lg transition-shadow duration-300">
        <CardContent className="p-6">
          <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center mb-4", color)}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          <h3 className="text-xl font-semibold mb-4">{title}</h3>
          <ul className="space-y-3">
            {benefits.map((benefit, i) => (
              <li key={i} className="flex items-start gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0 mt-0.5" />
                <span className="text-sm text-muted-foreground">{benefit}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// Feature highlight
function FeatureHighlight({
  icon: Icon,
  title,
  description,
  delay,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      whileInView={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay }}
      viewport={{ once: true }}
      className="flex items-start gap-4"
    >
      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
        <Icon className="w-5 h-5 text-primary" />
      </div>
      <div>
        <h4 className="font-medium mb-1">{title}</h4>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </motion.div>
  );
}

export function LandingPage({ onGetStarted }: LandingPageProps) {
  const [activeStep, setActiveStep] = useState(0);

  const workflowSteps = [
    {
      icon: FileText,
      title: 'Requirements',
      description: 'Analyze repos, generate epics & user stories with acceptance criteria',
      color: 'bg-purple-500',
      agent: 'Requirements Agent',
    },
    {
      icon: Target,
      title: 'Planning',
      description: 'Break down stories into tasks, estimate effort, create milestones',
      color: 'bg-blue-500',
      agent: 'Planning Agent',
    },
    {
      icon: Code,
      title: 'Development',
      description: 'Generate code, create PRs, implement features following best practices',
      color: 'bg-green-500',
      agent: 'Developer Agent',
    },
    {
      icon: Shield,
      title: 'Testing',
      description: 'Write unit tests, integration tests, ensure quality standards',
      color: 'bg-cyan-500',
      agent: 'Tester Agent',
    },
    {
      icon: Rocket,
      title: 'Deployment',
      description: 'Prepare releases, manage CI/CD pipelines, deploy to environments',
      color: 'bg-orange-500',
      agent: 'DevOps Agent',
    },
  ];

  const roles = [
    {
      icon: Users,
      title: 'Business Stakeholders',
      color: 'bg-purple-500',
      benefits: [
        'Get clear visibility into project progress and timelines',
        'Automatic requirement traceability from idea to deployment',
        'Real-time metrics and dashboards for decision making',
        'Reduced time-to-market with automated workflows',
      ],
    },
    {
      icon: Target,
      title: 'Product Managers',
      color: 'bg-blue-500',
      benefits: [
        'AI-generated user stories from high-level objectives',
        'Automatic story point estimation and sprint planning',
        'Full backlog management with epic/story hierarchy',
        'GitHub integration for seamless issue tracking',
      ],
    },
    {
      icon: Palette,
      title: 'Designers',
      color: 'bg-pink-500',
      benefits: [
        'Clear acceptance criteria for every user story',
        'Traceability from design requirements to implementation',
        'Visibility into development progress on your designs',
        'Collaborative workflow with developers and PMs',
      ],
    },
    {
      icon: Code,
      title: 'Software Developers',
      color: 'bg-green-500',
      benefits: [
        'AI-assisted code generation following your patterns',
        'Automatic test generation for your features',
        'GitHub PR creation with detailed descriptions',
        'Focus on complex problems while AI handles boilerplate',
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/30">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-grid-pattern opacity-5" />
        <div className="container mx-auto px-4 py-20 md:py-32">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-4xl mx-auto"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
              <Sparkles className="w-4 h-4" />
              <span>AI-Powered Software Development</span>
            </div>
            
            <h1 className="text-4xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
              Transform Ideas into
              <br />
              <span className="text-primary">Production-Ready Software</span>
            </h1>
            
            <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
              SDLC Agent orchestrates the entire software development lifecycle using 
              specialized AI agents—from requirements gathering to deployment—all while 
              keeping your team in control.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button size="lg" onClick={onGetStarted} className="gap-2">
                Get Started
                <ArrowRight className="w-4 h-4" />
              </Button>
              <Button size="lg" variant="outline" className="gap-2">
                <Play className="w-4 h-4" />
                Watch Demo
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* How It Works - Workflow Visualization */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">How It Works</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Our multi-agent system handles every phase of software development, 
              with an intelligent orchestrator coordinating the workflow.
            </p>
          </motion.div>

          {/* Orchestrator Hub */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
            className="flex justify-center mb-12"
          >
            <div className="relative">
              <div className="w-32 h-32 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center shadow-2xl">
                <Brain className="w-16 h-16 text-white" />
              </div>
              <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 whitespace-nowrap">
                <span className="px-4 py-1.5 rounded-full bg-background border text-sm font-medium shadow-sm">
                  Orchestrator Agent
                </span>
              </div>
              {/* Animated rings */}
              <div className="absolute inset-0 -z-10">
                <div className="absolute inset-0 animate-ping rounded-full bg-primary/20" style={{ animationDuration: '3s' }} />
                <div className="absolute inset-[-20px] animate-ping rounded-full bg-primary/10" style={{ animationDuration: '3s', animationDelay: '0.5s' }} />
              </div>
            </div>
          </motion.div>

          {/* Connection lines (simplified) */}
          <div className="hidden md:flex justify-center mb-8">
            <svg width="800" height="60" className="text-border">
              <path
                d="M 100 0 L 100 30 M 250 0 L 250 30 M 400 0 L 400 30 M 550 0 L 550 30 M 700 0 L 700 30"
                stroke="currentColor"
                strokeWidth="2"
                strokeDasharray="4 4"
                fill="none"
              />
              <path
                d="M 100 30 Q 100 50 200 50 L 600 50 Q 700 50 700 30"
                stroke="currentColor"
                strokeWidth="2"
                fill="none"
              />
            </svg>
          </div>

          {/* Workflow Steps */}
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
            {workflowSteps.map((step, index) => (
              <WorkflowStep
                key={step.title}
                {...step}
                isActive={activeStep === index}
                delay={index * 0.1}
              />
            ))}
          </div>

          {/* Workflow arrows for mobile */}
          <div className="flex md:hidden justify-center my-4">
            <div className="flex flex-col items-center gap-2 text-muted-foreground">
              <ArrowRight className="w-6 h-6 rotate-90" />
              <span className="text-xs">Automated Flow</span>
            </div>
          </div>
        </div>
      </section>

      {/* Key Capabilities */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
              viewport={{ once: true }}
            >
              <h2 className="text-3xl md:text-4xl font-bold mb-6">
                Enterprise-Grade
                <br />
                <span className="text-primary">AI Development Platform</span>
              </h2>
              <p className="text-lg text-muted-foreground mb-8">
                Built for real-world software development with enterprise security, 
                GitHub integration, and complete traceability from requirements to deployment.
              </p>
              
              <div className="space-y-6">
                <FeatureHighlight
                  icon={GitBranch}
                  title="GitHub Integration"
                  description="Seamlessly sync with your repositories, create issues, and open pull requests automatically."
                  delay={0.1}
                />
                <FeatureHighlight
                  icon={Layers}
                  title="Full Traceability"
                  description="Track every requirement through design, development, testing, and deployment phases."
                  delay={0.2}
                />
                <FeatureHighlight
                  icon={BarChart3}
                  title="Real-Time Metrics"
                  description="Monitor agent performance, token usage, and project progress with live dashboards."
                  delay={0.3}
                />
                <FeatureHighlight
                  icon={Zap}
                  title="Intelligent Automation"
                  description="AI agents learn from your codebase patterns and adapt to your team's conventions."
                  delay={0.4}
                />
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
              viewport={{ once: true }}
              className="relative"
            >
              {/* Mockup of the dashboard */}
              <div className="rounded-2xl border bg-card shadow-2xl overflow-hidden">
                <div className="h-8 bg-muted border-b flex items-center px-4 gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500" />
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span className="text-xs text-muted-foreground ml-2">SDLC Agent Dashboard</span>
                </div>
                <div className="p-6 space-y-4">
                  {/* Mini backlog visualization */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Active Workflow</span>
                      <span className="text-xs px-2 py-1 rounded-full bg-green-500/10 text-green-500">Running</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div className="h-full w-2/3 rounded-full bg-gradient-to-r from-purple-500 via-blue-500 to-green-500" />
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <CircleDot className="w-3 h-3 text-purple-500" />
                        <span>3 Epics</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <CircleDot className="w-3 h-3 text-blue-500" />
                        <span>12 Stories</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <CircleDot className="w-3 h-3 text-green-500" />
                        <span>28 Tasks</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Agent activity */}
                  <div className="border-t pt-4 space-y-2">
                    <span className="text-sm font-medium">Recent Agent Activity</span>
                    <div className="space-y-2">
                      {[
                        { agent: 'Requirements', action: 'Created user story US-015', time: '2m ago', color: 'bg-purple-500' },
                        { agent: 'Planning', action: 'Estimated 5 story points', time: '5m ago', color: 'bg-blue-500' },
                        { agent: 'Developer', action: 'Generated AuthService.ts', time: '8m ago', color: 'bg-green-500' },
                      ].map((activity, i) => (
                        <div key={i} className="flex items-center gap-3 text-xs">
                          <div className={cn("w-2 h-2 rounded-full", activity.color)} />
                          <span className="text-muted-foreground">{activity.agent}:</span>
                          <span className="flex-1 truncate">{activity.action}</span>
                          <span className="text-muted-foreground">{activity.time}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Floating badges */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.3 }}
                viewport={{ once: true }}
                className="absolute -left-6 top-1/4 px-4 py-2 rounded-lg bg-background border shadow-lg"
              >
                <div className="flex items-center gap-2">
                  <Bot className="w-5 h-5 text-primary" />
                  <span className="text-sm font-medium">5 AI Agents</span>
                </div>
              </motion.div>
              
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.5 }}
                viewport={{ once: true }}
                className="absolute -right-6 bottom-1/4 px-4 py-2 rounded-lg bg-background border shadow-lg"
              >
                <div className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-yellow-500" />
                  <span className="text-sm font-medium">10x Faster</span>
                </div>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Role-Based Benefits */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Built for Your Team</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Whether you're a business stakeholder, product manager, designer, or developer, 
              SDLC Agent streamlines your workflow and amplifies your impact.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {roles.map((role, index) => (
              <RoleCard key={role.title} {...role} delay={index * 0.1} />
            ))}
          </div>
        </div>
      </section>

      {/* The SDLC Agent Difference */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">The SDLC Agent Difference</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Unlike simple code generators, SDLC Agent understands the complete 
              software development lifecycle and orchestrates specialized agents for each phase.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                title: 'Multi-Agent Architecture',
                description: 'Each phase of development is handled by a specialized AI agent, ensuring expert-level execution at every step.',
                icon: Brain,
              },
              {
                title: 'Intelligent Orchestration',
                description: 'The Orchestrator Agent coordinates the workflow, manages handoffs, and ensures seamless progression through phases.',
                icon: GitBranch,
              },
              {
                title: 'Human-in-the-Loop',
                description: 'Stay in control with approval gates, real-time monitoring, and the ability to intervene at any point in the process.',
                icon: Users,
              },
            ].map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                viewport={{ once: true }}
                className="text-center"
              >
                <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <feature.icon className="w-8 h-8 text-primary" />
                </div>
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-muted-foreground">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary text-primary-foreground">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
            className="text-center max-w-3xl mx-auto"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Ready to Transform Your Development Process?
            </h2>
            <p className="text-xl opacity-90 mb-8">
              Start your first AI-powered project in minutes. Connect your GitHub repository 
              and let our agents do the heavy lifting.
            </p>
            <Button 
              size="lg" 
              variant="secondary" 
              onClick={onGetStarted}
              className="gap-2"
            >
              Start Your First Project
              <ArrowRight className="w-4 h-4" />
            </Button>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Brain className="w-6 h-6 text-primary" />
              <span className="font-semibold">SDLC Agent</span>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2026 SDLC Agent. AI-Powered Software Development Platform.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
