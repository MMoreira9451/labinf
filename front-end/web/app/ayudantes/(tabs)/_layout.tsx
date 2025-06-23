import React from 'react';
import { Tabs } from 'expo-router';
import { Text, View, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';

export default function AyudantesTabLayout() {
  const router = useRouter();

  const HeaderBackButton = () => (
    <TouchableOpacity
      onPress={() => router.push('/')}
      style={{ marginLeft: 10 }}
    >
      <Ionicons name="home" size={24} color="white" />
    </TouchableOpacity>
  );

  return (
    <Tabs
      screenOptions={({ route }) => ({
        tabBarIcon: () => {
          const icons: { [key: string]: string } = {
            index: '🔄',
            registros: '📝',
            cumplimiento: '✅',
            horas: '⏱️',
            ayudantes: '👨‍🔬',
          };
          return (
            <View style={{ alignItems: 'center' }}>
              <Text style={{ fontSize: 22 }}>{icons[route.name] || '📱'}</Text>
            </View>
          );
        },
        tabBarLabel: () => {
          const labels: { [key: string]: string } = {
            index: 'Generar QR',
            registros: 'Registros',
            cumplimiento: 'Cumplimiento',
            horas: 'Horas',
            ayudantes: 'Ayudantes',
          };
          return <Text style={{ fontSize: 12, color: 'white' }}>{labels[route.name] || 'Tab'}</Text>;
        },
        tabBarStyle: {
          height: 60,
          paddingBottom: 5,
          backgroundColor: '#e74c3c',
        },
        headerStyle: {
          backgroundColor: '#e74c3c',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
        headerLeft: () => <HeaderBackButton />,
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