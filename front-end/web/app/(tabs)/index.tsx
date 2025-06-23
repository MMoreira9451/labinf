// app/(tabs)/index.tsx
import React from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

const { width } = Dimensions.get('window');

export default function PortalSelector() {
  const router = useRouter();

  const navigateToEstudiantes = () => {
    router.push('/estudiantes');
  };

  const navigateToAyudantes = () => {
    router.push('/ayudantes');
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Sistema de Control de Acceso</Text>
        <Text style={styles.subtitle}>Laboratorio de Informática</Text>
        <Text style={styles.description}>
          Selecciona el portal correspondiente para acceder al sistema
        </Text>
      </View>

      <View style={styles.buttonsContainer}>
        <TouchableOpacity 
          style={[styles.portalButton, styles.estudiantesButton]}
          onPress={navigateToEstudiantes}
          activeOpacity={0.8}
        >
          <View style={styles.iconContainer}>
            <Ionicons name="school-outline" size={60} color="white" />
          </View>
          <Text style={styles.buttonTitle}>Portal Estudiantes</Text>
          <Text style={styles.buttonDescription}>
            Generación de QR, consulta de estudiantes y registros de acceso
          </Text>
          <View style={styles.arrowContainer}>
            <Ionicons name="arrow-forward" size={24} color="white" />
          </View>
        </TouchableOpacity>

        <TouchableOpacity 
          style={[styles.portalButton, styles.ayudantesButton]}
          onPress={navigateToAyudantes}
          activeOpacity={0.8}
        >
          <View style={styles.iconContainer}>
            <Ionicons name="people-outline" size={60} color="white" />
          </View>
          <Text style={styles.buttonTitle}>Portal Ayudantes</Text>
          <Text style={styles.buttonDescription}>
            QR de ayudantes, registros, cumplimiento y control de horas
          </Text>
          <View style={styles.arrowContainer}>
            <Ionicons name="arrow-forward" size={24} color="white" />
          </View>
        </TouchableOpacity>
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Universidad Adolfo Ibañez - Facultad de Ciencias
        </Text>
        <Text style={styles.footerSubtext}>
          Departamento de informatica
        </Text>
      </View>

      <StatusBar style="light" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f7fa',
    paddingHorizontal: 20,
  },
  header: {
    alignItems: 'center',
    paddingTop: 40,
    paddingBottom: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2c3e50',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 18,
    color: '#34495e',
    marginBottom: 12,
    fontWeight: '600',
  },
  description: {
    fontSize: 16,
    color: '#7f8c8d',
    textAlign: 'center',
    lineHeight: 22,
    paddingHorizontal: 20,
  },
  buttonsContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 30,
  },
  portalButton: {
    width: width - 40,
    minHeight: 180,
    borderRadius: 20,
    padding: 30,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
    position: 'relative',
  },
  estudiantesButton: {
    backgroundColor: '#3498db',
  },
  ayudantesButton: {
    backgroundColor: '#e74c3c',
  },
  iconContainer: {
    marginBottom: 15,
  },
  buttonTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 10,
    textAlign: 'center',
  },
  buttonDescription: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.9)',
    textAlign: 'center',
    lineHeight: 20,
    paddingHorizontal: 10,
  },
  arrowContainer: {
    position: 'absolute',
    right: 25,
    top: '50%',
    transform: [{ translateY: -12 }],
  },
  footer: {
    alignItems: 'center',
    paddingVertical: 30,
  },
  footerText: {
    fontSize: 14,
    color: '#7f8c8d',
    fontWeight: '600',
  },
  footerSubtext: {
    fontSize: 12,
    color: '#95a5a6',
    marginTop: 4,
  },
});