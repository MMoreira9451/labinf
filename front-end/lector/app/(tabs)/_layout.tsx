import { Tabs } from 'expo-router';
import React from 'react';
import { Platform } from 'react-native';

import { HapticTab } from '@/components/HapticTab';
import { IconSymbol } from '@/components/ui/IconSymbol';
import TabBarBackground from '@/components/ui/TabBarBackground';
import { Colors } from '@/constants/Colors';
import { useColorScheme } from '@/hooks/useColorScheme';

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? 'light'].tint,
        headerShown: false,
        tabBarButton: HapticTab,
        tabBarBackground: TabBarBackground,
        tabBarStyle: Platform.select({
          ios: {
            position: 'absolute',
          },
          default: {
            // Ocultar tab bar en pantallas pequeñas
            display: 'none',
          },
        }),
      }}>
      <Tabs.Screen
        name="index"
        options={{
          title: 'Lector QR',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="qr-code-scanner" color={color} />,
        }}
      />
      <Tabs.Screen
        name="stats"
        options={{
          title: 'Estadísticas',
          tabBarIcon: ({ color }) => <IconSymbol size={28} name="bar-chart" color={color} />,
        }}
      />
    </Tabs>
  );
}