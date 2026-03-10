import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  MessageSquare, Send, FileText, History, Settings, LogOut, 
  Users, Menu, X, Bell, Contact, ChevronDown, LayoutDashboard,
  Megaphone
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const Layout = ({ children, user, onLogout }) => {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const isAdmin = user?.role === 'admin';
  const features = user?.features || {};

  // Define all available features with their nav items
  const featureNavItems = {
    bulk_messages: { name: 'Send Messages', path: '/send', icon: Send },
    reminders: { name: 'Reminders', path: '/reminders', icon: Bell },
    contacts: { name: 'Contacts', path: '/contacts', icon: Contact },
    templates: { name: 'My Templates', path: '/my-templates', icon: FileText },
    campaigns: { name: 'Campaigns', path: '/campaigns', icon: History },
    indiamart: { name: 'Indiamart Leads', path: '/indiamart', icon: Megaphone },
  };

  // Build navigation based on user's enabled features
  const buildUserNav = () => {
    const navItems = [
      { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    ];

    // Add feature-specific items if enabled
    Object.entries(featureNavItems).forEach(([featureKey, navItem]) => {
      if (features[featureKey] !== false) { // Default to showing if not explicitly disabled
        navItems.push(navItem);
      }
    });

    navItems.push({ name: 'Settings', path: '/settings', icon: Settings });
    return navItems;
  };

  const adminNav = [
    { name: 'Dashboard', path: '/admin', icon: Users },
    { name: 'Reminders', path: '/reminders', icon: Bell },
    { name: 'Contacts', path: '/contacts', icon: Contact },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  const navItems = isAdmin ? adminNav : buildUserNav();

  // Group nav items for dropdown - main items shown directly, others in "More" dropdown
  const mainNavItems = navItems.slice(0, 4); // First 4 items shown directly
  const moreNavItems = navItems.slice(4); // Rest in dropdown

  const isActive = (path) => location.pathname === path;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100">
      {/* Top Navigation Bar */}
      <nav className="bg-white shadow-sm border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-14">
            {/* Logo */}
            <Link to={isAdmin ? '/admin' : '/dashboard'} className="flex items-center space-x-2">
              <div className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-blue-700 shadow">
                <MessageSquare className="h-4 w-4 text-white" />
              </div>
              <span className="text-base font-semibold text-slate-900 hidden sm:block">
                WhatsApp Messenger
              </span>
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-1">
              {mainNavItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.path);
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    data-testid={`nav-${item.name.toLowerCase().replace(/\s+/g, '-')}`}
                  >
                    <Button
                      variant={active ? 'default' : 'ghost'}
                      size="sm"
                      className={`${
                        active
                          ? 'bg-blue-600 text-white hover:bg-blue-700'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                      }`}
                    >
                      <Icon className="h-4 w-4 mr-1.5" />
                      <span className="text-sm">{item.name}</span>
                    </Button>
                  </Link>
                );
              })}

              {/* More dropdown for additional items */}
              {moreNavItems.length > 0 && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm" className="text-slate-600">
                      More
                      <ChevronDown className="h-4 w-4 ml-1" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    {moreNavItems.map((item) => {
                      const Icon = item.icon;
                      return (
                        <DropdownMenuItem key={item.path} asChild>
                          <Link to={item.path} className="flex items-center">
                            <Icon className="h-4 w-4 mr-2" />
                            {item.name}
                          </Link>
                        </DropdownMenuItem>
                      );
                    })}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}

              {/* User menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="ml-2">
                    <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-medium text-sm">
                      {user?.firstName?.charAt(0) || 'U'}
                    </div>
                    <ChevronDown className="h-3 w-3 ml-1 text-slate-400" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <div className="px-2 py-1.5">
                    <p className="text-sm font-medium">{user?.firstName} {user?.lastName}</p>
                    <p className="text-xs text-slate-500">{user?.email}</p>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link to="/settings" className="flex items-center">
                      <Settings className="h-4 w-4 mr-2" />
                      Settings
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    onClick={onLogout}
                    className="text-red-600 focus:text-red-600 focus:bg-red-50"
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Mobile menu button */}
            <div className="md:hidden">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                data-testid="mobile-menu-button"
              >
                {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </Button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-200 bg-white">
            <div className="px-2 pt-2 pb-3 space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.path);
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center space-x-3 px-3 py-2 rounded-lg ${
                      active
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    <span className="font-medium">{item.name}</span>
                  </Link>
                );
              })}
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  onLogout();
                }}
                className="flex items-center space-x-3 px-3 py-2 rounded-lg text-red-600 hover:bg-red-50 w-full"
              >
                <LogOut className="h-5 w-5" />
                <span className="font-medium">Logout</span>
              </button>
            </div>
          </div>
        )}
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white/50 backdrop-blur-sm border-t border-slate-200 mt-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-xs text-slate-500">
            © 2025 WhatsApp Bulk Messenger
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
