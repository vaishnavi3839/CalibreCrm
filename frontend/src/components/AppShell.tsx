"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bell,
  BookOpen,
  Calendar,
  ClipboardList,
  FileText,
  GraduationCap,
  Home,
  LogOut,
  PhoneCall,
  QrCode,
  Target,
  UserCircle,
  Users,
  BarChart3,
  Wallet,
} from "lucide-react";
import { BrandLogo } from "@/components/Brand";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

type NavItem = { href: string; label: string; icon: React.ComponentType<{ className?: string }> };

const ADMIN_NAV: NavItem[] = [
  { href: "/app/admin", label: "Pulse", icon: Home },
  { href: "/app/leads", label: "Leads", icon: Users },
  { href: "/app/followups", label: "Follow-ups", icon: PhoneCall },
  { href: "/app/staff", label: "Staff", icon: Users },
  { href: "/app/branches", label: "Branches", icon: QrCode },
  { href: "/app/reports/daily", label: "Daily Report", icon: BarChart3 },
  { href: "/app/students", label: "Students", icon: GraduationCap },
  { href: "/app/parents", label: "Parents", icon: Users },
  { href: "/app/courses", label: "Courses", icon: BookOpen },
  { href: "/app/documents", label: "Documents", icon: FileText },
  { href: "/app/attendance", label: "Attendance", icon: ClipboardList },
  { href: "/app/punch", label: "QR Punch", icon: QrCode },
  { href: "/app/punch/admin", label: "Punch Control", icon: QrCode },
  { href: "/app/salary", label: "Salary", icon: Wallet },
  { href: "/app/events", label: "Events", icon: Calendar },
  { href: "/app/meetings", label: "Meetings", icon: Calendar },
  { href: "/app/announcements", label: "Notices", icon: Bell },
  { href: "/app/tasks", label: "Tasks", icon: ClipboardList },
  { href: "/app/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/app/profile", label: "Profile", icon: UserCircle },
];

const RM_NAV: NavItem[] = [
  { href: "/app/rm", label: "Dashboard", icon: Home },
  { href: "/app/leads", label: "Leads", icon: Users },
  { href: "/app/followups", label: "Follow-ups", icon: PhoneCall },
  { href: "/app/staff", label: "Staff", icon: Users },
  { href: "/app/reports/daily", label: "Daily Report", icon: BarChart3 },
  { href: "/app/punch", label: "QR Punch", icon: QrCode },
  { href: "/app/salary", label: "Salary", icon: Wallet },
  { href: "/app/performance", label: "Performance", icon: Target },
  { href: "/app/analytics", label: "Funnel", icon: BarChart3 },
  { href: "/app/events", label: "Events", icon: Calendar },
  { href: "/app/meetings", label: "Meetings", icon: Calendar },
  { href: "/app/announcements", label: "Notices", icon: Bell },
  { href: "/app/tasks", label: "Tasks", icon: ClipboardList },
  { href: "/app/profile", label: "Profile", icon: UserCircle },
];

const TELE_NAV: NavItem[] = [
  { href: "/app/telecaller", label: "Home", icon: Home },
  { href: "/app/punch", label: "QR Punch", icon: QrCode },
  { href: "/app/salary", label: "Salary", icon: Wallet },
  { href: "/app/telecaller/leads", label: "Leads", icon: Users },
  { href: "/app/telecaller/followups", label: "Follow-ups", icon: PhoneCall },
  { href: "/app/telecaller/tasks", label: "Tasks", icon: ClipboardList },
  { href: "/app/meetings", label: "Meetings", icon: Calendar },
  { href: "/app/announcements", label: "Notices", icon: Bell },
  { href: "/app/telecaller/performance", label: "Performance", icon: Target },
  { href: "/app/profile", label: "Profile", icon: UserCircle },
];

const STUDENT_NAV: NavItem[] = [
  { href: "/app/student", label: "Home", icon: Home },
  { href: "/app/punch", label: "QR Punch", icon: QrCode },
  { href: "/app/student/course", label: "Course", icon: BookOpen },
  { href: "/app/student/attendance", label: "Attendance", icon: ClipboardList },
  { href: "/app/student/documents", label: "Documents", icon: FileText },
  { href: "/app/student/id", label: "ID", icon: GraduationCap },
  { href: "/app/meetings", label: "Meetings", icon: Calendar },
  { href: "/app/announcements", label: "Notices", icon: Bell },
  { href: "/app/profile", label: "Profile", icon: UserCircle },
];

const PARENT_NAV: NavItem[] = [
  { href: "/app/parent", label: "Home", icon: Home },
  { href: "/app/parent/attendance", label: "Attendance", icon: ClipboardList },
  { href: "/app/parent/progress", label: "Progress", icon: Target },
  { href: "/app/parent/documents", label: "Documents", icon: FileText },
  { href: "/app/parent/announcements", label: "Notices", icon: Bell },
  { href: "/app/meetings", label: "Meetings", icon: Calendar },
  { href: "/app/notifications", label: "Alerts", icon: Bell },
  { href: "/app/profile", label: "Profile", icon: UserCircle },
];

function navForRole(role: string): NavItem[] {
  if (role === "telecaller") return TELE_NAV;
  if (role === "student") return STUDENT_NAV;
  if (role === "parent") return PARENT_NAV;
  if (role === "rm") return RM_NAV;
  if (role === "instructor") {
    return [
      { href: "/app/instructor", label: "Home", icon: Home },
      { href: "/app/punch", label: "QR Punch", icon: QrCode },
      { href: "/app/salary", label: "Salary", icon: Wallet },
      { href: "/app/students", label: "Students", icon: Users },
      { href: "/app/attendance", label: "Attendance", icon: ClipboardList },
      { href: "/app/exams", label: "Exams", icon: BookOpen },
      { href: "/app/meetings", label: "Meetings", icon: Calendar },
      { href: "/app/announcements", label: "Notices", icon: Bell },
      { href: "/app/tasks", label: "Tasks", icon: ClipboardList },
      { href: "/app/profile", label: "Profile", icon: UserCircle },
    ];
  }
  return ADMIN_NAV;
}

function avatarSrc(user: { full_name: string; photo_url?: string | null }) {
  return (
    user.photo_url ||
    `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(user.full_name.replace(/\s/g, ""))}&backgroundColor=0a1628`
  );
}

export function AppShell({
  children,
  title,
  subtitle,
}: {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
}) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  if (!user) return null;

  const nav = navForRole(user.role.name);

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 flex w-56 flex-col bg-navy-900 text-white sm:w-64">
        <div className="flex items-center gap-3 border-b border-white/10 px-3 py-4 sm:px-4 sm:py-5">
          <BrandLogo className="h-12 w-auto shrink-0 sm:h-14" />
          <div className="min-w-0">
            <div className="truncate font-[family-name:var(--font-display)] text-base leading-tight sm:text-lg">
              Calibre
            </div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-brass-400 sm:text-[11px]">
              Aviation Academy
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-4 sm:px-3">
          {nav.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
                  active ? "bg-white/10 text-white" : "text-white/70 hover:bg-white/5 hover:text-white"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/10 p-3 sm:p-4">
          <Link href="/app/profile" className="mb-3 flex items-center gap-3 rounded-xl px-1 py-1 hover:bg-white/5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={avatarSrc(user)} alt="" className="h-10 w-10 rounded-full border border-brass-500/40 object-cover" />
            <div className="min-w-0 text-sm">
              <div className="truncate font-medium">{user.full_name}</div>
              <div className="text-xs text-white/50">{user.role.display_name}</div>
            </div>
          </Link>
          <button
            onClick={async () => {
              await logout();
              router.push("/login");
            }}
            className="flex w-full items-center gap-2 rounded-xl bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>

      <div className="pl-56 sm:pl-64">
        <header className="sticky top-0 z-20 border-b border-navy-900/5 bg-white/70 backdrop-blur-md">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
            <div>
              <h1 className="text-lg font-semibold text-navy-900 sm:text-xl">{title || "Dashboard"}</h1>
              {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
            </div>
            <div className="flex items-center gap-2">
              <Link href="/app/profile" className="rounded-full">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={avatarSrc(user)} alt="Profile" className="h-9 w-9 rounded-full border border-cloud-200 object-cover" />
              </Link>
              <Link href="/app/notifications" className="rounded-full bg-cloud-100 p-2 text-navy-800">
                <Bell className="h-5 w-5" />
              </Link>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 py-5 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
