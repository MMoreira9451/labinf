import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { apiService } from '@/services/ApiService';
import { Config } from '@/constants/Config';

interface Stats {
  success: boolean;
  date: string;
  students: {
    entries: number;
    exits: number;
  };
  helpers: {
    entries: number;
    exits: number;
  };
  error?: string;
}

interface Record {
  tipo_usuario: 'ESTUDIANTE' | 'AYUDANTE';
  nombre: string;
  apellido: string;
  email: string;
  fecha: string;
  hora: string;
  tipo: 'Entrada' | 'Salida';
}

export default function StatsScreen() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [records, setRecords] = useState<Record[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchData = async () => {
    try {
      // Obtener estadísticas
      const statsData = await apiService.getStats();
      if (statsData.success) {
        setStats(statsData);
      } else {
        throw new Error(statsData.error || 'Error obteniendo estadísticas');
      }

      // Obtener últimos registros
      const recordsData = await apiService.getLastRecords(15);
      if (recordsData.success) {
        setRecords(recordsData.records);
      } else {
        throw new Error(recordsData.error || 'Error obteniendo registros');
      }

      setLastUpdate(new Date());

    } catch (error) {
      console.error('Error fetching data:', error);
      Alert.alert('Error de Conexión',
        error instanceof Error ? error.message : 'No se pudieron cargar los datos'
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Auto-refresh cada 30 segundos
    const interval = setInterval(fetchData, 30000);

    return () => clearInterval(interval);
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const formatTime = (timeString: string) => {
    return timeString.slice(0, 5); // HH:MM
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const formatLastUpdate = () => {
    return lastUpdate.toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Ionicons name="refresh" size={50} color={Config.UI.COLORS.PRIMARY} />
        <Text style={styles.loadingText}>Cargando estadísticas...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          colors={[Config.UI.COLORS.PRIMARY]}
          tintColor={Config.UI.COLORS.PRIMARY}
        />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Estadísticas del Día</Text>
        <Text style={styles.headerDate}>
          {stats?.date ? formatDate(stats.date) : 'N/A'}
        </Text>
        <Text style={styles.lastUpdate}>
          Última actualización: {formatLastUpdate()}
        </Text>
      </View>

      {/* Botón de actualización manual */}
      <TouchableOpacity
        style={styles.refreshButton}
        onPress={onRefresh}
        disabled={refreshing}
      >
        <Ionicons
          name={refreshing ? "refresh" : "refresh-outline"}
          size={24}
          color={Config.UI.COLORS.WHITE}
        />
        <Text style={styles.refreshButtonText}>
          {refreshing ? 'Actualizando...' : 'Actualizar Datos'}
        </Text>
      </TouchableOpacity>

      {/* Estadísticas */}
      {stats && (
        <View style={styles.statsContainer}>
          {/* Estudiantes */}
          <View style={[styles.statCard, styles.studentsCard]}>
            <View style={styles.statHeader}>
              <Ionicons name="school" size={28} color={Config.UI.COLORS.SUCCESS} />
              <Text style={styles.statTitle}>Estudiantes</Text>
            </View>
            <View style={styles.statNumbers}>
              <View style={styles.statItem}>
                <Text style={[styles.statNumber, { color: Config.UI.COLORS.SUCCESS }]}>
                  {stats.students.entries}
                </Text>
                <Text style={styles.statLabel}>Entradas</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.statItem}>
                <Text style={[styles.statNumber, { color: Config.UI.COLORS.PRIMARY }]}>
                  {stats.students.exits}
                </Text>
                <Text style={styles.statLabel}>Salidas</Text>
              </View>
            </View>
          </View>

          {/* Ayudantes */}
          <View style={[styles.statCard, styles.helpersCard]}>
            <View style={styles.statHeader}>
              <Ionicons name="people" size={28} color={Config.UI.COLORS.PRIMARY} />
              <Text style={styles.statTitle}>Ayudantes</Text>
            </View>
            <View style={styles.statNumbers}>
              <View style={styles.statItem}>
                <Text style={[styles.statNumber, { color: Config.UI.COLORS.SUCCESS }]}>
                  {stats.helpers.entries}
                </Text>
                <Text style={styles.statLabel}>Entradas</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.statItem}>
                <Text style={[styles.statNumber, { color: Config.UI.COLORS.PRIMARY }]}>
                  {stats.helpers.exits}
                </Text>
                <Text style={styles.statLabel}>Salidas</Text>
              </View>
            </View>
          </View>

          {/* Total */}
          <View style={[styles.statCard, styles.totalCard]}>
            <View style={styles.statHeader}>
              <Ionicons name="analytics" size={28} color={Config.UI.COLORS.WARNING} />
              <Text style={styles.statTitle}>Total General</Text>
            </View>
            <View style={styles.statNumbers}>
              <View style={styles.statItem}>
                <Text style={[styles.statNumber, { color: Config.UI.COLORS.SUCCESS }]}>
                  {stats.students.entries + stats.helpers.entries}
                </Text>
                <Text style={styles.statLabel}>Entradas</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.statItem}>
                <Text style={[styles.statNumber, { color: Config.UI.COLORS.PRIMARY }]}>
                  {stats.students.exits + stats.helpers.exits}
                </Text>
                <Text style={styles.statLabel}>Salidas</Text>
              </View>
            </View>
            <View style={styles.totalFooter}>
              <Text style={styles.totalText}>
                Personas presentes: {
                  (stats.students.entries - stats.students.exits) +
                  (stats.helpers.entries - stats.helpers.exits)
                }
              </Text>
            </View>
          </View>
        </View>
      )}

      {/* Últimos registros */}
      <View style={styles.recordsContainer}>
        <View style={styles.recordsHeader}>
          <Text style={styles.recordsTitle}>Últimos Registros</Text>
          <View style={styles.recordsHeaderRight}>
            <Text style={styles.recordsCount}>
              {records.length} registros
            </Text>
          </View>
        </View>

        {records.length > 0 ? (
          records.map((record, index) => (
            <View key={index} style={styles.recordItem}>
              <View style={styles.recordLeft}>
                <View style={[
                  styles.recordTypeIcon,
                  {
                    backgroundColor: record.tipo === 'Entrada'
                      ? Config.UI.COLORS.SUCCESS
                      : Config.UI.COLORS.PRIMARY
                  }
                ]}>
                  <Ionicons
                    name={record.tipo === 'Entrada' ? 'enter' : 'exit'}
                    size={18}
                    color={Config.UI.COLORS.WHITE}
                  />
                </View>
                <View style={styles.recordInfo}>
                  <Text style={styles.recordName}>
                    {record.nombre} {record.apellido}
                  </Text>
                  <Text style={styles.recordType}>
                    {record.usuario_tipo}
                  </Text>
                </View>
              </View>
              <View style={styles.recordRight}>
                <Text style={[
                  styles.recordAction,
                  {
                    color: record.tipo === 'Entrada'
                      ? Config.UI.COLORS.SUCCESS
                      : Config.UI.COLORS.PRIMARY
                  }
                ]}>
                  {record.tipo}
                </Text>
                <Text style={styles.recordTime}>
                  {formatTime(record.hora)}
                </Text>
              </View>
            </View>
          ))
        ) : (
          <View style={styles.noRecords}>
            <Ionicons name="document-text-outline" size={50} color={Config.UI.COLORS.TEXT_LIGHT} />
            <Text style={styles.noRecordsText}>No hay registros recientes</Text>
            <TouchableOpacity style={styles.retryButton} onPress={onRefresh}>
              <Text style={styles.retryButtonText}>Intentar de nuevo</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Información adicional */}
      <View style={styles.infoContainer}>
        <View style={styles.infoItem}>
          <Ionicons name="information-circle" size={20} color={Config.UI.COLORS.PRIMARY} />
          <Text style={styles.infoText}>
            Los datos se actualizan automáticamente cada 30 segundos
          </Text>
        </View>
        <View style={styles.infoItem}>
          <Ionicons name="wifi" size={20} color={Config.UI.COLORS.SUCCESS} />
          <Text style={styles.infoText}>
            Conectado a: {Config.API_BASE_URL.replace('https://', '')}
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Config.UI.COLORS.BACKGROUND,
  },

  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Config.UI.COLORS.BACKGROUND,
  },
  loadingText: {
    marginTop: 15,
    fontSize: 18,
    color: Config.UI.COLORS.TEXT_LIGHT,
    fontWeight: '500',
  },

  header: {
    backgroundColor: Config.UI.COLORS.PRIMARY,
    padding: 20,
    alignItems: 'center',
  },
  headerTitle: {
    color: Config.UI.COLORS.WHITE,
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  headerDate: {
    color: '#E3F2FD',
    fontSize: 16,
    fontWeight: '500',
  },
  lastUpdate: {
    color: '#BBDEFB',
    fontSize: 12,
    marginTop: 5,
  },

  refreshButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Config.UI.COLORS.SUCCESS,
    margin: 15,
    padding: 15,
    borderRadius: 10,
    gap: 10,
  },
  refreshButtonText: {
    color: Config.UI.COLORS.WHITE,
    fontSize: 16,
    fontWeight: 'bold',
  },

  statsContainer: {
    padding: 15,
    gap: 15,
  },
  statCard: {
    backgroundColor: Config.UI.COLORS.WHITE,
    borderRadius: 12,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 4,
  },
  studentsCard: {
    borderLeftWidth: 5,
    borderLeftColor: Config.UI.COLORS.SUCCESS,
  },
  helpersCard: {
    borderLeftWidth: 5,
    borderLeftColor: Config.UI.COLORS.PRIMARY,
  },
  totalCard: {
    borderWidth: 2,
    borderColor: Config.UI.COLORS.WARNING,
  },
  statHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  statTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: Config.UI.COLORS.TEXT,
    marginLeft: 12,
  },
  statNumbers: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  statItem: {
    alignItems: 'center',
    flex: 1,
  },
  statNumber: {
    fontSize: 36,
    fontWeight: 'bold',
  },
  statLabel: {
    fontSize: 14,
    color: Config.UI.COLORS.TEXT_LIGHT,
    marginTop: 8,
    fontWeight: '500',
  },
  statDivider: {
    width: 1,
    height: 40,
    backgroundColor: '#E0E0E0',
    marginHorizontal: 10,
  },
  totalFooter: {
    marginTop: 15,
    paddingTop: 15,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
    alignItems: 'center',
  },
  totalText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: Config.UI.COLORS.WARNING,
  },

  recordsContainer: {
    margin: 15,
    backgroundColor: Config.UI.COLORS.WHITE,
    borderRadius: 12,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 4,
  },
  recordsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
    paddingBottom: 10,
    borderBottomWidth: 2,
    borderBottomColor: '#E0E0E0',
  },
  recordsTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: Config.UI.COLORS.TEXT,
  },
  recordsHeaderRight: {
    alignItems: 'flex-end',
  },
  recordsCount: {
    fontSize: 12,
    color: Config.UI.COLORS.TEXT_LIGHT,
  },
  recordItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  recordLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  recordTypeIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  recordInfo: {
    marginLeft: 15,
    flex: 1,
  },
  recordName: {
    fontSize: 16,
    fontWeight: '600',
    color: Config.UI.COLORS.TEXT,
  },
  recordType: {
    fontSize: 12,
    color: Config.UI.COLORS.TEXT_LIGHT,
    marginTop: 2,
    fontWeight: '500',
  },
  recordRight: {
    alignItems: 'flex-end',
  },
  recordAction: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  recordTime: {
    fontSize: 14,
    color: Config.UI.COLORS.TEXT_LIGHT,
    marginTop: 2,
    fontWeight: '500',
  },
  noRecords: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  noRecordsText: {
    fontSize: 18,
    color: Config.UI.COLORS.TEXT_LIGHT,
    marginTop: 15,
    marginBottom: 20,
  },
  retryButton: {
    backgroundColor: Config.UI.COLORS.PRIMARY,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  retryButtonText: {
    color: Config.UI.COLORS.WHITE,
    fontSize: 14,
    fontWeight: 'bold',
  },

  infoContainer: {
    margin: 15,
    backgroundColor: Config.UI.COLORS.WHITE,
    borderRadius: 12,
    padding: 15,
    gap: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  infoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  infoText: {
    fontSize: 12,
    color: Config.UI.COLORS.TEXT_LIGHT,
    flex: 1,
  },
});