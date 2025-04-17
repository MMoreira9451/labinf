// app/cumplimiento.tsx
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl, TouchableOpacity } from 'react-native';
import { Platform } from 'react-native';

const API_BASE = Platform.OS === 'web'
  ? 'http://10.0.5.63:5000'
  : 'http://10.0.5.63:8081';

export default function CumplimientoScreen() {
  const [cumplimiento, setCumplimiento] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [view, setView] = useState('resumen');

  const loadCumplimiento = () => {
    setRefreshing(true);
    fetch(`${API_BASE}/cumplimiento`)
      .then(res => res.json())
      .then(data => {
        setCumplimiento(Array.isArray(data) ? data : []);
        setRefreshing(false);
      })
      .catch(err => {
        console.error(err);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    loadCumplimiento();
    const interval = setInterval(loadCumplimiento, 300000);
    return () => clearInterval(interval);
  }, []);

  const onRefresh = () => {
    loadCumplimiento();
  };

  const stats = {
    total: cumplimiento.length,
    cumpliendo: cumplimiento.filter(item => item.estado === 'Cumpliendo').length,
    incompleto: cumplimiento.filter(item => item.estado === 'Incompleto').length,
    ausente: cumplimiento.filter(item => item.estado === 'Ausente').length,
    retrasado: cumplimiento.filter(item => item.estado === 'Retrasado').length,
    noAplica: cumplimiento.filter(item => item.estado === 'No Aplica').length,
  };

  const getStatusColor = (estado) => {
    switch (estado) {
      case 'Cumpliendo': return '#4CAF50';
      case 'Incompleto': return '#FF9800';
      case 'Ausente': return '#F44336';
      case 'Retrasado': return '#FFC107';
      case 'No Aplica': return '#9E9E9E';
      default: return '#9E9E9E';
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Cumplimiento de horarios</Text>

      <View style={styles.viewToggle}>
        <TouchableOpacity 
          style={[styles.toggleButton, view === 'resumen' && styles.toggleActive]}
          onPress={() => setView('resumen')}
        >
          <Text style={styles.toggleText}>Resumen</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={[styles.toggleButton, view === 'detalle' && styles.toggleActive]}
          onPress={() => setView('detalle')}
        >
          <Text style={styles.toggleText}>Detalle</Text>
        </TouchableOpacity>
      </View>

      {view === 'resumen' ? (
        <View style={styles.statsContainer}>
          {Object.entries(stats).map(([key, value]) => (
            key !== 'total' && (
              <View key={key} style={styles.statCard}>
                <Text style={styles.statValue}>{value}</Text>
                <Text style={styles.statLabel}>{
                  key === 'cumpliendo' ? 'Cumpliendo' :
                  key === 'incompleto' ? 'Incompleto' :
                  key === 'ausente' ? 'Ausente' :
                  key === 'retrasado' ? 'Retrasado' :
                  key === 'noAplica' ? 'No aplica' : key
                }</Text>
                <View style={[styles.statusIndicator, { backgroundColor: getStatusColor(key.charAt(0).toUpperCase() + key.slice(1)) }]} />
              </View>
            )
          ))}
        </View>
      ) : (
        <FlatList
          data={cumplimiento}
          keyExtractor={(item, index) => `${item.email}-${index}`}
          renderItem={({ item }) => (
            <View style={styles.cumplimientoItem}>
              <Text style={styles.cumplimientoNombre}>{item.nombre} {item.apellido}</Text>
              <View style={[styles.cumplimientoEstado, { backgroundColor: getStatusColor(item.estado) }]}>
                <Text style={styles.cumplimientoEstadoText}>{item.estado}</Text>
              </View>
              {item.bloques?.length > 0 ? (
                <View style={styles.bloquesContainer}>
                  {item.bloques.map((bloque, idx) => (
                    <View key={idx} style={styles.bloqueItem}>
                      <Text style={styles.bloqueHora}>{bloque.inicio} - {bloque.fin}</Text>
                      <Text style={styles.bloqueEstado}>{bloque.estado || 'Pendiente'}</Text>
                    </View>
                  ))}
                </View>
              ) : item.estado === 'No Aplica' && (
                <Text style={styles.noScheduleText}>Sin horario programado para hoy</Text>
              )}
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
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  viewToggle: {
    flexDirection: 'row',
    marginBottom: 15,
    justifyContent: 'center',
  },
  toggleButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: 'white',
    marginHorizontal: 5,
    borderRadius: 5,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  toggleActive: {
    backgroundColor: '#1890ff',
    borderColor: '#1890ff',
  },
  toggleText: {
    color: '#333',
  },
  statsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statCard: {
    width: '48%',
    backgroundColor: 'white',
    padding: 15,
    marginBottom: 15,
    borderRadius: 10,
    alignItems: 'center',
    position: 'relative',
  },
  statValue: {
    fontSize: 32,
    fontWeight: 'bold',
  },
  statLabel: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
  },
  statusIndicator: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: 10,
    height: '100%',
    borderTopLeftRadius: 10,
    borderBottomLeftRadius: 10,
  },
  cumplimientoItem: {
    padding: 15,
    marginBottom: 10,
    backgroundColor: 'white',
    borderRadius: 5,
  },
  cumplimientoNombre: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 5,
  },
  cumplimientoEstado: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 15,
    marginBottom: 10,
  },
  cumplimientoEstadoText: {
    color: 'white',
    fontWeight: '500',
  },
  bloquesContainer: {
    marginTop: 5,
  },
  bloqueItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 5,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  bloqueHora: {
    color: '#666',
  },
  bloqueEstado: {
    fontWeight: '500',
  },
  noScheduleText: {
    fontStyle: 'italic',
    color: '#757575',
    marginTop: 8,
  },
  lastUpdate: {
    textAlign: 'center',
    fontSize: 12,
    color: '#999',
    marginTop: 10,
  },
});
