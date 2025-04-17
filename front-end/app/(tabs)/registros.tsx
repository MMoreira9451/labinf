// app/registros.tsx
import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View, FlatList, RefreshControl, TouchableOpacity, ScrollView } from 'react-native';
import { Platform } from 'react-native';

const API_BASE = Platform.OS === 'web'
  ? 'http://10.0.5.123:5000'
  : 'http://10.0.5.63:8081';

export default function RegistrosScreen() {
  const [registros, setRegistros] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [filtroPersona, setFiltroPersona] = useState(null);

  const loadRegistros = () => {
    setRefreshing(true);
    fetch(`${API_BASE}/registros_hoy`)
      .then(res => res.json())
      .then(data => {
        setRegistros(data);
        setRefreshing(false);
      })
      .catch(err => {
        console.error(err);
        setRefreshing(false);
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
    const registrosPersona = todosRegistros
      .filter(r => r.email === registro.email)
      .sort((a, b) => new Date(`2000-01-01T${a.hora}`) - new Date(`2000-01-01T${b.hora}`));

    const idx = registrosPersona.findIndex(r => r.id === registro.id || (r.hora === registro.hora && r.nombre === registro.nombre));
    return idx % 2 === 0 ? 'Entrada' : 'Salida';
  };

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
});
