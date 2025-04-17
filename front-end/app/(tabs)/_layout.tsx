// app/_layout.tsx
import React from 'react';
import { Tabs } from 'expo-router';
import { Text, View } from 'react-native';

export default function AppLayout() {
  return (
    <Tabs
      screenOptions={({ route }) => ({
        tabBarIcon: () => {
          const icons = {
            index: '🔄',
            registros: '📝',
            cumplimiento: '✅',
            horas: '⏱️',
            ayudantes: '👨‍🔬',
          };
          return (
            <View style={{ alignItems: 'center' }}>
              <Text style={{ fontSize: 22 }}>{icons[route.name]}</Text>
            </View>
          );
        },
        tabBarLabel: () => {
          const labels = {
            index: 'Generar QR',
            registros: 'Registros',
            cumplimiento: 'Cumplimiento',
            horas: 'Horas',
            ayudantes: 'Ayudantes',
          };
          return <Text style={{ fontSize: 12, color: 'white' }}>{labels[route.name]}</Text>;
        },
        tabBarStyle: {
          height: 60,
          paddingBottom: 5,
          backgroundColor: '#000000', // Cambiado de #1890ff a negro
        },
      })}
    >
      <Tabs.Screen name="index" options={{ title: 'Generar QR' }} />
      <Tabs.Screen name="registros" options={{ title: 'Registros' }} />
      <Tabs.Screen name="cumplimiento" options={{ title: 'Cumplimiento' }} />
      <Tabs.Screen name="horas" options={{ title: 'Horas' }} />
      <Tabs.Screen name="ayudantes" options={{ title: 'Ayudantes' }} />
    </Tabs>
  );
}