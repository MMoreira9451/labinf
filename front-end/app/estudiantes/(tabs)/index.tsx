// app/(tabs)/index.tsx
import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Platform,
  ActivityIndicator
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Clipboard from 'expo-clipboard';
import QRCode from 'react-native-qrcode-svg';
import { StatusBar } from 'expo-status-bar';

// Constante para la URL de la API
const API_BASE = Platform.OS === 'web'
  ? 'http://10.0.3.54:5000'
  : 'http://10.0.3.54:8081'; // Reemplazar si se usa Expo Go en móvil

export default function QRGeneratorScreen() {
  const [name, setName] = useState('');
  const [surname, setSurname] = useState('');
  const [email, setEmail] = useState('');
  const [savedUsers, setSavedUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [autoRenewal, setAutoRenewal] = useState(false);
  const [renewInterval, setRenewInterval] = useState(null);
  const [qrExpired, setQrExpired] = useState(false);
  
  useEffect(() => {
    loadSavedUsers();
    return () => {
      if (renewInterval) clearInterval(renewInterval);
    };
  }, []);

  const loadSavedUsers = async () => {
    try {
      const storedUsers = await AsyncStorage.getItem('savedUsers');
      if (storedUsers !== null) {
        setSavedUsers(JSON.parse(storedUsers));
      }
    } catch (error) {
      console.error('Error loading users:', error);
    }
  };

  const saveUser = async () => {
    if (name.trim() === '' || surname.trim() === '' || email.trim() === '' || !email.includes('@')) {
      alert('Por favor ingresa datos válidos');
      return;
    }

    const timestamp = Date.now();
    const userData = { 
      name: name.trim(), 
      surname: surname.trim(), 
      email: email.trim(), 
      timestamp, 
      expired: false, 
      tipoUsuario: 'ESTUDIANTE' // Identificador explícito de estudiante
    };

    try {
      const newUsers = [...savedUsers, userData];
      await AsyncStorage.setItem('savedUsers', JSON.stringify(newUsers));
      setSavedUsers(newUsers);
      setSelectedUser(userData);
      setQrExpired(false);

      // Limpiar cualquier intervalo existente
      if (renewInterval) {
        clearInterval(renewInterval);
        setRenewInterval(null);
      }

      // Configurar auto-renovación o QR expirado
      if (autoRenewal) {
        const interval = setInterval(() => {
          const newTimestamp = Date.now();
          setSelectedUser(prevUser => ({
            ...prevUser,
            timestamp: newTimestamp,
            expired: false
          }));
        }, 14000); // Renovar cada 14 segundos
        setRenewInterval(interval);
      } else {
        // Establecer expiración después de 15 segundos
        setTimeout(() => {
          setQrExpired(true);
          setSelectedUser(prevUser => ({
            ...prevUser,
            expired: true
          }));
        }, 15000);
      }

      setName('');
      setSurname('');
      setEmail('');
    } catch (error) {
      console.error('Error saving user:', error);
    }
  };

  const toggleAutoRenewal = () => {
    const newAutoRenewal = !autoRenewal;
    setAutoRenewal(newAutoRenewal);
    
    // Limpiar cualquier intervalo existente
    if (renewInterval) {
      clearInterval(renewInterval);
      setRenewInterval(null);
    }

    if (selectedUser) {
      if (newAutoRenewal) {
        // Activar auto-renovación
        const interval = setInterval(() => {
          const newTimestamp = Date.now();
          setSelectedUser(prevUser => ({
            ...prevUser,
            timestamp: newTimestamp,
            expired: false
          }));
          setQrExpired(false);
        }, 14000);
        setRenewInterval(interval);
      } else if (qrExpired) {
        // Ya expirado, mantenerlo así
        setSelectedUser(prevUser => ({
          ...prevUser,
          expired: true
        }));
      } else {
        // Establecer expiración después de 15 segundos
        setTimeout(() => {
          setQrExpired(true);
          setSelectedUser(prevUser => {
            if (prevUser) {
              return {
                ...prevUser,
                expired: true
              };
            }
            return null;
          });
        }, 15000);
      }
    }
  };

  const selectSavedUser = (user) => {
    // Limpiar cualquier intervalo existente
    if (renewInterval) {
      clearInterval(renewInterval);
      setRenewInterval(null);
    }
    
    setName(user.name);
    setSurname(user.surname);
    setEmail(user.email);
    
    // Al seleccionar un usuario existente, generar un nuevo QR con timestamp actual
    const timestamp = Date.now();
    const updatedUser = { ...user, timestamp, expired: false };
    setSelectedUser(updatedUser);
    setQrExpired(false);
    
    // Configurar expiración o auto-renovación
    if (autoRenewal) {
      const interval = setInterval(() => {
        const newTimestamp = Date.now();
        setSelectedUser(prevUser => ({
          ...prevUser,
          timestamp: newTimestamp,
          expired: false
        }));
      }, 14000);
      setRenewInterval(interval);
    } else {
      setTimeout(() => {
        setQrExpired(true);
        setSelectedUser(prevUser => ({
          ...prevUser,
          expired: true
        }));
      }, 15000);
    }
  };

  // Generar valor QR como objeto JSON válido con codificación adecuada
  const generateQrValue = () => {
    if (!selectedUser) return JSON.stringify({});
  
    // Asegurar codificación de cadena adecuada eliminando espacios finales y normalizando texto
    const sanitizedUser = {
      name: selectedUser.name.trim(),
      surname: selectedUser.surname.trim(),
      email: selectedUser.email.trim(),
      timestamp: selectedUser.timestamp,
      tipoUsuario: 'ESTUDIANTE'  // Identificador explícito de estudiante
    };
  
    // Agregar propiedades adicionales basadas en el estado
    if (qrExpired && !autoRenewal) {
      return JSON.stringify({
        ...sanitizedUser,
        expired: true,
        status: "EXPIRED"
      });
    }
  
    if (autoRenewal) {
      return JSON.stringify({
        ...sanitizedUser,
        timestamp: Date.now(),
        autoRenewal: true,
        status: "VALID"
      });
    }
  
    return JSON.stringify({
      ...sanitizedUser,
      status: "VALID"
    });
  };

  // Copiar URL del QR
  const copyQrData = async () => {
    if (selectedUser) {
      await Clipboard.setStringAsync(generateQrValue());
      alert('Datos del QR copiados al portapapeles');
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Generador QR para Estudiantes</Text>
      <TextInput style={styles.input} placeholder="Nombre" value={name} onChangeText={setName} />
      <TextInput style={styles.input} placeholder="Apellido" value={surname} onChangeText={setSurname} />
      <TextInput 
        style={styles.input} 
        placeholder="Email institucional" 
        value={email} 
        onChangeText={setEmail} 
        keyboardType="email-address" 
        autoCapitalize="none" 
      />
      
      <View style={styles.optionsRow}>
        <TouchableOpacity 
          style={styles.generateButton} 
          onPress={saveUser}
        >
          <Text style={styles.generateButtonText}>Generar QR</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          onPress={toggleAutoRenewal} 
          style={[styles.checkboxContainer, autoRenewal && styles.checkboxChecked]}
        >
          <Text style={styles.checkboxText}>Auto-renovar QR</Text>
        </TouchableOpacity>
      </View>

      {savedUsers.length > 0 && (
        <ScrollView horizontal style={styles.userList}>
          {savedUsers.map((user, idx) => (
            <TouchableOpacity 
              key={idx} 
              style={styles.userItem}
              onPress={() => selectSavedUser(user)}
            >
              <Text style={styles.userItemText}>{user.name} {user.surname}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {selectedUser && (
        <View style={styles.qrContainer}>
          <Text style={[
            styles.userText, 
            (qrExpired && !autoRenewal) ? styles.expiredText : styles.validText
          ]}>
            {(qrExpired && !autoRenewal) 
              ? 'QR Expirado' 
              : `${selectedUser.name} ${selectedUser.surname} - ${selectedUser.email}`
            }
          </Text>
          
          <QRCode
            value={generateQrValue()}
            size={200}
            backgroundColor="white"
            color={(qrExpired && !autoRenewal) ? "#cccccc" : "black"}
          />
          
          <View style={styles.userInfoContainer}>
            <Text style={styles.userInfoText}>
              <Text style={styles.infoLabel}>Nombre: </Text>
              {selectedUser.name} {selectedUser.surname}
            </Text>
            <Text style={styles.userInfoText}>
              <Text style={styles.infoLabel}>Email: </Text>
              {selectedUser.email}
            </Text>
            <Text style={styles.userInfoText}>
              <Text style={styles.infoLabel}>Tipo: </Text>
              <Text style={styles.tipoText}>ESTUDIANTE</Text>
            </Text>
          </View>
          
          {autoRenewal && (
            <Text style={styles.renewalText}>QR con renovación automática activa</Text>
          )}
          
          {!autoRenewal && !qrExpired && (
            <Text style={styles.expirationText}>
              Este QR expirará en 15 segundos
            </Text>
          )}
          
          <View style={styles.actionButtons}>
            <TouchableOpacity style={styles.actionButton} onPress={copyQrData}>
              <Ionicons name="copy-outline" size={20} color="#1890ff" />
              <Text style={styles.actionButtonText}>Copiar datos</Text>
            </TouchableOpacity>
            
            {(qrExpired && !autoRenewal) && (
              <TouchableOpacity 
                style={styles.actionButton}
                onPress={() => {
                  const newTimestamp = Date.now();
                  setSelectedUser(prevUser => ({
                    ...prevUser,
                    timestamp: newTimestamp,
                    expired: false
                  }));
                  setQrExpired(false);
                  
                  setTimeout(() => {
                    setQrExpired(true);
                    setSelectedUser(prevUser => ({
                      ...prevUser,
                      expired: true
                    }));
                  }, 15000);
                }}
              >
                <Ionicons name="refresh" size={20} color="#1890ff" />
                <Text style={styles.actionButtonText}>Renovar</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
      )}
      <StatusBar style="auto" />
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
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 5,
    marginBottom: 10,
    paddingHorizontal: 10,
    backgroundColor: 'white',
  },
  optionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  generateButton: {
    backgroundColor: '#0066CC',
    paddingVertical: 10,
    paddingHorizontal: 15,
    borderRadius: 5,
  },
  generateButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 5,
    backgroundColor: 'white',
  },
  checkboxChecked: {
    backgroundColor: '#e6f7ff',
    borderColor: '#1890ff',
  },
  checkboxText: {
    marginLeft: 5,
  },
  userList: {
    maxHeight: 50,
    marginVertical: 10,
  },
  userItem: {
    padding: 10,
    marginRight: 10,
    backgroundColor: '#e6f7ff',
    borderRadius: 5,
  },
  userItemText: {
    color: '#1890ff',
  },
  qrContainer: {
    alignItems: 'center',
    marginTop: 20,
    padding: 20,
    backgroundColor: 'white',
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  userText: {
    fontSize: 16,
    marginBottom: 15,
    fontWeight: '500',
    textAlign: 'center',
  },
  expiredText: {
    color: '#ff4d4f',
  },
  validText: {
    color: '#52c41a',
  },
  userInfoContainer: {
    marginTop: 15,
    backgroundColor: '#f9f9f9',
    padding: 10,
    borderRadius: 5,
    width: '100%',
  },
  userInfoText: {
    marginBottom: 5,
  },
  infoLabel: {
    fontWeight: 'bold',
  },
  tipoText: {
    color: '#0066CC',
    fontWeight: 'bold',
  },
  renewalText: {
    marginTop: 10,
    color: '#1890ff',
    fontStyle: 'italic',
  },
  expirationText: {
    marginTop: 10,
    color: '#999',
    fontStyle: 'italic',
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    width: '100%',
    marginTop: 15,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f0f8ff',
    padding: 8,
    borderRadius: 5,
  },
  actionButtonText: {
    color: '#1890ff',
    marginLeft: 5,
  },
});