import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export const useAppStore = create(
  devtools(
    (set, get) => ({
      // UI State
      loading: false,
      sidebarCollapsed: false,
      
      // User State
      user: {
        name: 'Admin User',
        role: 'Administrator',
        avatar: null,
      },
      
      // Notifications
      notifications: [
        {
          id: 1,
          type: 'info',
          title: 'Test Plan Generated',
          message: 'New test plan "5G_NR_PHY_Tests" has been generated successfully',
          timestamp: new Date().toISOString(),
          read: false,
        },
        {
          id: 2,
          type: 'success',
          title: 'PICS Upload Complete',
          message: 'PICS file uploaded and processed successfully',
          timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
          read: false,
        },
        {
          id: 3,
          type: 'warning',
          title: 'Report Generation Delayed',
          message: 'Some reports are taking longer than expected to generate',
          timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
          read: true,
        },
      ],
      
      // Actions
      setLoading: (loading) => set({ loading }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      
      // Notification Actions
      markNotificationAsRead: (id) =>
        set((state) => ({
          notifications: state.notifications.map((notif) =>
            notif.id === id ? { ...notif, read: true } : notif
          ),
        })),
      
      addNotification: (notification) =>
        set((state) => ({
          notifications: [
            {
              ...notification,
              id: Date.now(),
              timestamp: new Date().toISOString(),
              read: false,
            },
            ...state.notifications,
          ],
        })),
      
      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((notif) => notif.id !== id),
        })),
    }),
    {
      name: 'app-store',
    }
  )
)