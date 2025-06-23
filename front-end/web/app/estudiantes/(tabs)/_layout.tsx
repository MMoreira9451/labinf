import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';

export default function EstudiantesTabLayout() {
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
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: keyof typeof Ionicons.glyphMap = 'help-outline';

          if (route.name === 'index') {
            iconName = 'qr-code-outline';
          } else if (route.name === 'estudiantes') {
            iconName = 'people-outline';
          } else if (route.name === 'registros') {
            iconName = 'list-outline';
          }

          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#3498db',
        tabBarInactiveTintColor: 'gray',
        headerStyle: {
          backgroundColor: '#3498db',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
        headerLeft: () => <HeaderBackButton />,
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
