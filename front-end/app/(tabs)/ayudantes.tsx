// app/ayudantes.tsx
import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View, FlatList, Platform, RefreshControl, Image } from 'react-native';

const API_BASE = Platform.OS === 'web'
  ? 'http://10.0.5.63:5000'
  : 'http://10.0.5.63:8081';

export default function AyudantesScreen() {
  const [ayudantes, setAyudantes] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const loadAyudantes = () => {
    setRefreshing(true);
    fetch(`${API_BASE}/ayudantes_presentes`)
      .then(res => res.json())
      .then(data => {
        setAyudantes(data);
        setLastUpdated(new Date());
        setRefreshing(false);
      })
      .catch(err => {
        console.error('Error al cargar los ayudantes presentes:', err);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    loadAyudantes();
    const interval = setInterval(loadAyudantes, 120000);
    return () => clearInterval(interval);
  }, []);

  const onRefresh = () => {
    loadAyudantes();
  };

  const getInitials = (nombre, apellido) => {
    return (nombre.charAt(0) + apellido.charAt(0)).toUpperCase();
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Ayudantes en el laboratorio</Text>

      {ayudantes.length === 0 && !refreshing ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No hay ayudantes en el laboratorio actualmente</Text>
        </View>
      ) : (
        <FlatList
          data={ayudantes}
          keyExtractor={(item) => item.email}
          numColumns={2}
          columnWrapperStyle={styles.ayudantesRow}
          renderItem={({ item }) => (
            <View style={styles.ayudanteCard}>
              <View style={styles.avatarContainer}>
                <View style={styles.avatarFallback}>
                  <Text style={styles.avatarInitials}>
                    {getInitials(item.nombre, item.apellido)}
                  </Text>
                </View>
                {item.foto_url ? (
                  <Image
                    source={{ uri: item.foto_url }}
                    style={styles.avatarImage}
                  />
                ) : null}
              </View>
              <Text style={styles.ayudanteNombre}>{item.nombre}</Text>
              <Text style={styles.ayudanteApellido}>{item.apellido}</Text>
              <Text style={styles.ayudanteEntrada}>Entrada: {item.ultima_entrada}</Text>
            </View>
          )}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
        />
      )}

      <Text style={styles.lastUpdate}>
        Última actualización: {lastUpdated.toLocaleTimeString()}
      </Text>
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
  ayudantesRow: {
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  ayudanteCard: {
    width: '48%',
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 15,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
    marginBottom: 15,
  },
  avatarContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#f0f0f0',
    marginBottom: 10,
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
    position: 'relative',
  },
  avatarImage: {
    width: 100,
    height: 100,
    borderRadius: 50,
    position: 'absolute',
    top: 0,
    left: 0,
    zIndex: 2,
  },
  avatarFallback: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#1890ff',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1,
  },
  avatarInitials: {
    color: 'white',
    fontSize: 40,
    fontWeight: 'bold',
  },
  ayudanteNombre: {
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  ayudanteApellido: {
    fontSize: 16,
    fontWeight: '500',
    textAlign: 'center',
  },
  ayudanteEntrada: {
    fontSize: 12,
    color: '#666',
    marginTop: 5,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    textAlign: 'center',
  },
  lastUpdate: {
    textAlign: 'center',
    fontSize: 12,
    color: '#999',
    marginTop: 10,
  },
});
