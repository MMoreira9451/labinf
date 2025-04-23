// app/registros.tsx
import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View, FlatList, RefreshControl, TouchableOpacity, ScrollView, ActivityIndicator } from 'react-native';
import { Platform } from 'react-native';

const API_BASE = Platform.OS === 'web'
  ? 'https://10.0.3.54:5000'
  : 'https://10.0.3.54:8081';

export default function RegistrosScreen() {
  const [registros, setRegistros] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filtroPersona, setFiltroPersona] = useState(null);

  const loadRegistros = () => {
    setRefreshing(true);
    setLoading(true);
    setError(null);
    
    fetch(`https://10.0.3.54:5000/registros_hoy`)
      .then(res => {
        if (!res.ok) {
          throw new Error(`Error ${res.status}: ${res.statusText || 'Error del servidor'}`);
        }
        return res.json();
      })
      .then(data => {
        // Asegurarse de que data es un array
        const registrosArray = Array.isArray(data) ? data : [];
        setRegistros(registrosArray);
        setRefreshing(false);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error al cargar registros:', err);
        setError(`No se pudieron cargar los registros: ${err.message}`);
        setRefreshing(false);
        setLoading(false);
        // En caso de error, inicializar registros como un array vacío
        setRegistros([]);
      });
  };

  useEffect(() => {
    loadRegistros();
    const interval = setInterval(loadRegistros, 300000);
    return () => clearInterval(interval);
  }, []);

  const onRefresh = () => {
    loadRegistros();
  };

  const getUniquePersonas = () => {
    // Verificar que registros sea un array antes de usar map
    if (!Array.isArray(registros) || registros.length === 0) {
      return [];
    }
    
    const uniqueEmails = [...new Set(registros.map(item => item.email))];
    return uniqueEmails.map(email => {
      const persona = registros.find(r => r.email === email);
      return {
        email,
        nombre: `${persona.nombre} ${persona.apellido}`,
      };
    });
  };

  const filteredRegistros = filtroPersona 
    ? registros.filter(item => item.email === filtroPersona)
    : registros;

  const getRegistroTipo = (registro, todosRegistros) => {
    // Asegurarse de que todosRegistros es un array
    if (!Array.isArray(todosRegistros) || todosRegistros.length === 0) {
      return 'Desconocido';
    }
    
    const registrosPersona = todosRegistros
      .filter(r => r.email === registro.email)
      .sort((a, b) => new Date(`2000-01-01T${a.hora}`) - new Date(`2000-01-01T${b.hora}`));

    const idx = registrosPersona.findIndex(r => 
      (r.id && registro.id && r.id === registro.id) || 
      (r.hora === registro.hora && r.nombre === registro.nombre)
    );
    
    return idx % 2 === 0 ? 'Entrada' : 'Salida';
  };

  // Mostrar indicador de carga mientras se cargan los datos
  if (loading && !refreshing) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#0066CC" />
        <Text style={styles.loadingText}>Cargando registros...</Text>
      </View>
    );
  }

  // Mostrar mensaje de error si ocurrió algún problema
  if (error) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadRegistros}>
          <Text style={styles.retryButtonText}>Reintentar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Registros de Hoy</Text>

      <ScrollView horizontal style={styles.filterContainer}>
        <TouchableOpacity 
          style={[styles.filterButton, filtroPersona === null && styles.filterActive]} 
          onPress={() => setFiltroPersona(null)}
        >
          <Text style={styles.filterText}>Todos</Text>
        </TouchableOpacity>

        {getUniquePersonas().map((persona, idx) => (
          <TouchableOpacity 
            key={idx} 
            style={[styles.filterButton, filtroPersona === persona.email && styles.filterActive]}
            onPress={() => setFiltroPersona(persona.email)}
          >
            <Text style={styles.filterText}>{persona.nombre}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {filteredRegistros.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No hay registros para mostrar</Text>
        </View>
      ) : (
        <FlatList
          data={filteredRegistros}
          keyExtractor={(item, index) => `${item.id || index}`}
          renderItem={({ item }) => (
            <View style={styles.registroItem}>
              <Text style={styles.registroNombre}>{item.nombre} {item.apellido}</Text>
              <Text style={styles.registroHora}>{item.hora}</Text>
              <Text style={styles.registroTipo}>{getRegistroTipo(item, filteredRegistros)}</Text>
            </View>
          )}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        />
      )}

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
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  errorText: {
    fontSize: 16,
    color: '#d32f2f',
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    backgroundColor: '#0066CC',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 5,
  },
  retryButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  filterContainer: {
    marginBottom: 10,
    maxHeight: 50,
  },
  filterButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    marginRight: 10,
    backgroundColor: 'white',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  filterActive: {
    backgroundColor: '#1890ff',
    borderColor: '#1890ff',
  },
  filterText: {
    color: '#333',
  },
  registroItem: {
    padding: 15,
    marginBottom: 10,
    backgroundColor: 'white',
    borderRadius: 5,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  registroNombre: {
    flex: 2,
    fontWeight: '500',
  },
  registroHora: {
    flex: 1,
    textAlign: 'center',
  },
  registroTipo: {
    flex: 1,
    textAlign: 'right',
    fontWeight: '500',
  },
  lastUpdate: {
    textAlign: 'center',
    fontSize: 12,
    color: '#999',
    marginTop: 10,
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
});
