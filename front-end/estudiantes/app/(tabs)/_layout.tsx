// app/(tabs)/_layout.js
import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          if (route.name === 'index') {
            iconName = 'qr-code-outline';
          } else if (route.name === 'estudiantes') {
            iconName = 'people-outline';
          } else if (route.name === 'registros') {
            iconName = 'list-outline';
          }

          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#0066CC',
        tabBarInactiveTintColor: 'gray',
        headerStyle: {
          backgroundColor: '#0066CC',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        }
      })}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Generador QR",
        }}
      />
      <Tabs.Screen
        name="estudiantes"
        options={{
          title: "Estudiantes",
        }}
      />
      <Tabs.Screen
        name="registros"
        options={{
          title: "Registros",
        }}
      />
    </Tabs>
  );
}