// app/horas.tsx
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl, TouchableOpacity, Platform } from 'react-native';

const API_BASE = Platform.OS === 'web'
  ? 'http://127.0.0.1:5000'
  : 'http://10.0.5.63:8081';

export default function HorasAcumuladasScreen() {
  const [horasData, setHorasData] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [sortBy, setSortBy] = useState('horas');

  const loadHorasAcumuladas = () => {
    setRefreshing(true);
    fetch(`${API_BASE}/horas_acumuladas`)
      .then(res => res.json())
      .then(data => {
        setHorasData(Array.isArray(data) ? data : []);
        setRefreshing(false);
      })
      .catch(err => {
        console.error('Error loading horas acumuladas:', err);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    loadHorasAcumuladas();
    const interval = setInterval(loadHorasAcumuladas, 900000);
    return () => clearInterval(interval);
  }, []);

  const onRefresh = () => {
    loadHorasAcumuladas();
  };

  const sortedData = [...horasData].sort((a, b) => {
    return sortBy === 'horas'
      ? b.horas_totales - a.horas_totales
      : a.nombre.localeCompare(b.nombre);
  });

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Horas Acumuladas</Text>

      <View style={styles.sortButtons}>
        <TouchableOpacity 
          style={[styles.sortButton, sortBy === 'horas' && styles.sortActive]}
          onPress={() => setSortBy('horas')}
        >
          <Text style={styles.sortButtonText}>Por Horas</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={[styles.sortButton, sortBy === 'nombre' && styles.sortActive]}
          onPress={() => setSortBy('nombre')}
        >
          <Text style={styles.sortButtonText}>Por Nombre</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={sortedData}
        keyExtractor={(item) => item.email}
        renderItem={({ item }) => (
          <View style={styles.horasItem}>
            <View style={styles.horasInfo}>
              <Text style={styles.horasNombre}>{item.nombre} {item.apellido}</Text>
              <Text style={styles.horasEmail}>{item.email}</Text>
            </View>
            <View style={styles.horasStats}>
              <View style={styles.horaStat}>
                <Text style={styles.horasStatValue}>{item.horas_totales}</Text>
                <Text style={styles.horasStatLabel}>Horas</Text>
              </View>
              <View style={styles.horaStat}>
                <Text style={styles.horasStatValue}>{item.dias_asistidos}</Text>
                <Text style={styles.horasStatLabel}>Días</Text>
              </View>
            </View>
          </View>
        )}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      />

      <Text style={styles.lastUpdate}>Última actualización: {new Date().toLocaleTimeString()}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 20,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  sortButtons: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 15,
  },
  sortButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    marginHorizontal: 10,
    backgroundColor: 'white',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  sortActive: {
    backgroundColor: '#1890ff',
    borderColor: '#1890ff',
  },
  sortButtonText: {
    color: '#333',
  },
  horasItem: {
    padding: 15,
    marginBottom: 10,
    backgroundColor: 'white',
    borderRadius: 5,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  horasInfo: {
    flex: 2,
  },
  horasNombre: {
    fontSize: 16,
    fontWeight: '500',
  },
  horasEmail: {
    fontSize: 12,
    color: '#666',
  },
  horasStats: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  horaStat: {
    alignItems: 'center',
  },
  horasStatValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1890ff',
  },
  horasStatLabel: {
    fontSize: 12,
    color: '#666',
  },
  lastUpdate: {
    textAlign: 'center',
    fontSize: 12,
    color: '#999',
    marginTop: 10,
  },
});
