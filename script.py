'''
PPGEE - Departamento de Engenharia Eletrica e de Computacao - UFBA
UR5: Cinematica Direta, Inversa e Planejamento de Trajetoria
Alunos: Andre Paiva Conrado Rodrigues e Gabriel Lucas Nascimento Silva
Disciplina: Sistemas Roboticos - 2024.1
Data: 14 ago 2024
'''

#-----------------------------------------------#
#----------Importacao de Dependencias-----------#
#-----------------------------------------------#

import numpy as np
from time import sleep

#-----------------------------------------------#
#---------------Variaveis Globais---------------#
#-----------------------------------------------#
SIGNAL = True

FLAG_DK = True # Flag que indica se a validacao da C.D. foi concluida
FLAG_IK = False # Flag que indica se a validacao da C.I. foi concluida
COUNTER_DK = 0 # Contador de casos de teste da C.D. que passaram por validacao
COUNTER_IK = 0 # Contador de casos de teste da C.I. que passaram por validacao

# Array de casos de teste da C.D (J1, J2, J3, J4, J5, J6)
TESTES_DH = np.array([  
                        [   30,     60,     90,     0,      0,       0    ],
                        [   0,      0,      0,      30,     60,      90   ],
                        [   -45,    -30,    60,     15,     -30,     75   ],
                        [   45,     -90,    75,     30,     -25,     -90  ],
                        [   39,     42,     -80,    9,      -112,    13   ],
                        [   -158,   97,     45,    -138,    125,     -147 ],
                        [   130,    -20,    -50,    -45,    25,      110  ],
                        [   0,      0,      0,      0,      0,       0    ],
                    ])

NUM_TESTES_DH = TESTES_DH.shape[0] # Quantidade de casos de teste da C.D.

# Array de casos de teste da C.I (X, Y, Z, Roll, Pitch, Yaw)
'''
TESTES_IK = np.array([
                        [   -0.4,      -0.4,      1.46,      0.4,      0.82,       0.9    ],
                        [   -0.4,      0.4,       1.37,      0.4,      0.82,       0.9    ],
                    ])
'''

TESTES_IK = []
for i in range(10):
    TESTES_IK.append(np.array([0.3*np.sin((i+1)*(0.07)) - 0.4,
                               0.3*np.sin((i+1)*(-0.07)) - 0.3,
                               (i+1)*(0.01) + 1.5,
                               0, #(i+1)*(-0.03),
                               np.pi/4, #(i+1)*0.03,
                               0, #(i+1)*(-0.03)
                               ]))
    
TESTES_IK = np.array(TESTES_IK)

NUM_TESTES_IK = TESTES_IK.shape[0]

#-----------------------------------------------#
#-------------Interacao CoppeliaSim-------------#
#-----------------------------------------------#

# Inicializacao
def sysCall_init():
    sim = require('sim')
    joints = get_joints()
    for joint in joints:
        sim.setJointMode(joint, sim.jointmode_kinematic, 1)
    #print(TESTES_IK)

# Validacoes implementadas no sensing
def sysCall_sensing():
    global FLAG_DK, COUNTER_DK, TESTES_DH, NUM_TESTES_DH
    global FLAG_IK, COUNTER_IK, TESTES_IK, NUM_TESTES_IK

    if((not FLAG_DK) and (not FLAG_IK)):
        if(COUNTER_DK >= NUM_TESTES_DH):
            FLAG_DK = True
        else:
            dk_validate(TESTES_DH, COUNTER_DK)
            COUNTER_DK += 1
    elif(FLAG_DK and (not FLAG_IK)):
        if(COUNTER_IK >= NUM_TESTES_IK):
            sleep(1)
            FLAG_IK = True
        else:
            ik_validate(TESTES_IK, COUNTER_IK)
            COUNTER_IK += 1

    '''
    print(ik_calculate(dk_get_end_effector_matrix()))
    print(read_joints_sensors())
    #print(ik_calculate(dk_get_end_effector_matrix()) - read_joints_sensors())
    print()
    '''

# Atuacao step-by-step
def sysCall_actuation():
    global SIGNAL

    '''
    joints = get_joints()
    for joint in joints:
        sim.setJointPosition(joint, 0)
    '''

    '''
    if(FLAG_DK and FLAG_IK):
        joints = get_joints()
        for joint in joints:
            orient = sim.getJointPosition(joint)
            if(orient > np.pi/2):
                SIGNAL = False
            elif(orient < -np.pi/2):
                SIGNAL = True
            if(SIGNAL):
                orient += 0.01
            else:
                orient -= 0.01
            sim.setJointPosition(joint, orient)
    '''

#-----------------------------------------------#
#--------------Funcoes Auxiliares---------------#
#-----------------------------------------------#

# Captura dos handlers das juntas
def get_joints():
    joints = []
    for i in range(6):
        joint = '/UR5/joint'
        if(i > 0):
            joint = '/UR5' + i * '/link/joint'
        joints.append(sim.getObject(joint))
    return joints

# Leitura de sensores das juntas
def read_joints_sensors():
    joints = get_joints()
    theta = []
    for joint in joints:
        theta.append(sim.getJointPosition(joint))
    return np.array(theta)

# Limita angulo entre -pi e pi
def wrap_angle(angle):
    return np.atan2(np.sin(angle),np.cos(angle))

# Montagem da matriz Ai
def mount_ai_matrix(a, alpha, d, theta):
    s_alp = np.sin(alpha)
    c_alp = np.cos(alpha)
    s_the = np.sin(theta)
    c_the = np.cos(theta)
    matrix = np.array([ [ c_the,    -s_the*c_alp,   s_the*s_alp,    a*c_the ],
                        [ s_the,    c_the*c_alp,    -c_the*s_alp,   a*s_the ],
                        [ 0,        s_alp,          c_alp,          d       ],
                        [ 0,        0,              0,              1       ]])
    return matrix

# Gera matriz de transformacao reversa
def reverse_transformation_matrix(matrix):
    rev_matrix = np.identity(4)
    rev_matrix[:3, :3] = np.array(matrix)[:3, :3].T
    rev_matrix[:3, 3] = np.matmul(-rev_matrix[:3, :3], np.array(matrix)[:3, 3])
    return rev_matrix

# Converte target_pose (X, Y, Z, R, P, Y) para matriz de transformacao
def pose2matrix(target_pose):
    roll = target_pose[3]
    pitch = target_pose[4]
    yaw = target_pose[5]

    roll_matrix = np.array([[1, 0, 0], [0, np.cos(roll), -np.sin(roll)], [0, np.sin(roll), np.cos(roll)]]) 
    pitch_matrix = np.array([[np.cos(pitch), 0, np.sin(pitch)], [0, 1, 0], [-np.sin(pitch), 0, np.cos(pitch)]]) 
    yaw_matrix = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])

    r_matrix = np.matmul(np.matmul(yaw_matrix, pitch_matrix), roll_matrix)

    t_matrix = np.identity(4)
    t_matrix[:3, :3] = r_matrix
    for i in range(3):
        t_matrix[i, 3] = target_pose[i]
    return t_matrix

def matrix2pose(target_matrix):
    x = target_matrix[0, 3]
    y = target_matrix[1, 3]
    z = target_matrix[2, 3]
    roll = np.atan2(target_matrix[2, 1], target_matrix[2, 2])
    pitch = np.atan2(-target_matrix[2, 0],  np.sqrt(target_matrix[2, 1]**2 + target_matrix[2, 2]**2))
    yaw = np.atan2(target_matrix[1, 0], target_matrix[0, 0])
    return np.array([x, y, z, roll, pitch, yaw])

def print_matrix(m):
    print(m)
    print(np.linalg.norm(m[:, 3] - np.array([0,0,0,1])))
    pose = matrix2pose(m)
    for i in range(3, 6):
        pose[i] *= 180/np.pi
    print(pose)
    print()

#-----------------------------------------------#
#---------Funcoes de Cinematica Direta----------#
#-----------------------------------------------#

# Tabela DH (a, alpha, d, theta)
def dk_get_dh():
    theta = read_joints_sensors()

    '''
    # Matriz adaptada para modelo do CoppeliaSim (com JacoHand)
    dh = np.array([ [    0,             -np.pi/2,   74.55e-3,            theta[0] + np.pi/2  ], # A1
                    [    425.1e-3,      0,          0,                   theta[1] - np.pi/2  ], # A2
                    [    392.15e-3,     0,          0,                   theta[2]            ], # A3
                    [    0,             -np.pi/2,   103.13e-3,           theta[3] - np.pi/2  ], # A4
                    [    0,             np.pi/2,    87.88e-3,            theta[4]            ], # A5
                    [    0,             0,          81.82e-3 + 56.2e-3,  theta[5]            ], # A6
                 ])
    
    '''
    # Matriz com valores encontrados em artigos (com JacoHand)
    dh = np.array([ [    0,             -np.pi/2,   89.159e-3,           theta[0] + np.pi/2  ], # A1
                    [    425e-3,        0,          0,                   theta[1] - np.pi/2  ], # A2
                    [    392.25e-3,     0,          0,                   theta[2]            ], # A3
                    [    0,             -np.pi/2,   109.15e-3,           theta[3] - np.pi/2  ], # A4
                    [    0,             np.pi/2,    94.65e-3,            theta[4]            ], # A5
                    [    0,             0,          82.3e-3 + 56.2e-3,   theta[5]            ], # A6
                 ])
    return dh

# Matriz Ai
def dk_get_ai(i):
    if i < 1 or i > 6:
        raise Exception('i deve estar entre 1 e 6')
    else:
        dh_line = dk_get_dh()[i-1]
        a_i = dh_line[0]
        alpha_i = dh_line[1]
        d_i = dh_line[2]
        theta_i = dh_line[3]
        matrix = mount_ai_matrix(a_i, alpha_i, d_i, theta_i)
        return matrix
        
# Matriz de transformacao completa
def dk_get_transformation_matrix():
    t_matrix = np.identity(4)
    for i in range(1, 7):
        t_matrix = np.matmul(t_matrix, dk_get_ai(i))
    return t_matrix

# Matriz de transformacao completa a partir de lista de ângulos
def dk_get_transformation_matrix_from_angles(joint_values):
    t_matrix = np.identity(4)
    dh = dk_get_dh()
    for i in range(0, 6):
        dh_line = dh[i]
        a = dh_line[0]
        alpha = dh_line[1]
        d = dh_line[2]
        theta = joint_values[i]
        if(i == 0):
            theta += np.pi/2
        elif(i == 1 or i == 3):
            theta -= np.pi/2
        ai_matrix = mount_ai_matrix(a, alpha, d, theta)
        t_matrix = np.matmul(t_matrix, ai_matrix)
    return t_matrix

# Posicao da garra
def dk_get_end_effector_matrix():
    base_matrix = sim.getObjectMatrix(sim.getObject("/UR5"))
    base_matrix = np.array([base_matrix[0:4],
                            base_matrix[4:8],
                            base_matrix[8:12],
                            [0, 0, 0, 1]])
    t_matrix = dk_get_transformation_matrix()
    end_effector_matrix = np.matmul(base_matrix, t_matrix)
    return end_effector_matrix

# Validacao Cinematica Direta
def dk_validate(test_cases, num_teste):
    TOLERANCE = 0.03    # Error tolerance in meters

    sleep(1)

    end_effector = sim.getObject("/UR5/JacoHand")
    #end_effector = sim.getObject("/UR5/connection")
    joints = get_joints()
    fail_count = 0

    print(f"========================================================")
    print(f"Validacao Cinematica Direta - Caso teste {num_teste+1}")
    print(f"========================================================")

    for joint, value in zip(joints, test_cases[num_teste]):
        sim.setJointPosition(joint, value*np.pi/180.0)
    end_pose = dk_get_end_effector_matrix()
    end_ground = np.array(sim.getObjectPosition(end_effector))
    end_diff = np.array([
                         end_pose[0][3] - end_ground[0],
                         end_pose[1][3] - end_ground[1], 
                         end_pose[2][3] - end_ground[2],
                         ])
    print(f"Angulos das Juntas: {test_cases[num_teste]}")
    print(f"Calculo Pose (X, Y, Z): {end_pose[0:3, 3]}")
    print(f"Truth (X, Y, Z):        {end_ground[0:3]}")
    print(f"Diff (X, Y, Z):         {end_diff}")
    for i in range(len(end_diff)):
        if abs(end_diff[i]) > TOLERANCE:
            fail_count += 1
            axis = ''
            if(i == 0):
                axis = 'X'
            elif(i == 1):
                axis = 'Y'
            elif(i == 2):
                axis = 'Z'
            print(f"FALHA: Diferenca de posicao do eixo {axis} fora da faixa de tolerancia")
    print(f"--------------------------------------------------------")
    
    if(fail_count == 0):
        print(f"Caso teste {num_teste+1} validado com exito.")
    else:
        print(f"Caso teste {num_teste+1} FALHOU com {fail_count} erros.")
    print(f"========================================================")
    print()

#-----------------------------------------------#
#--------Funcoes de Cinematica Inversa----------#
#-----------------------------------------------#

# Calcular Cinematica Inversa com base em target matrix
def ik_calculate(target_matrix):
    # Inicializacao das variaveis
    theta1 = theta2 = theta3 = theta4 = theta5 = theta6 = 0
    offset = np.array([np.pi/2, -np.pi/2, 0, -np.pi/2, 0, 0])

    # Obtencao de informacoes para o calculo
    dh = dk_get_dh()
    base_matrix = sim.getObjectMatrix(sim.getObject("/UR5"))
    base_matrix = np.array([base_matrix[0:4],
                            base_matrix[4:8],
                            base_matrix[8:12],
                            [0, 0, 0, 1]])
    rev_base = reverse_transformation_matrix(base_matrix)

    # Calculo do Theta 1
    d4 = dh[3, 2]
    d6 = dh[5, 2]
    T_0_6 = np.matmul(rev_base, target_matrix)
    P_0_5 = np.matmul(T_0_6, np.array([0, 0, -d6, 1]))
    p05x = P_0_5[0]
    p05y = P_0_5[1]
    theta1_sh_left = np.atan2(p05y, p05x) + np.acos(d4/np.sqrt(p05x**2 + p05y**2)) + np.pi/2
    theta1_sh_right = np.atan2(p05y, p05x) - np.acos(d4/np.sqrt(p05x**2 + p05y**2)) + np.pi/2
    
    '''
    #Se o ombro estiver pra a esquerda:
    current_theta2 = dh[1, 3] + np.pi/2
    if (current_theta2) >= 0:
        theta1 = wrap_angle(theta1_sh_left)
    else:
        theta1 = wrap_angle(theta1_sh_right)
    '''
    theta1 = wrap_angle(theta1_sh_left + offset[0])

    # Calculo do Theta 5
    p06x = T_0_6[0, 3]
    p06y = T_0_6[1, 3]
    acos_th5_param = (p06x*np.sin(theta1-offset[0])-p06y*np.cos(theta1-offset[0])-d4)/d6
    assert abs(acos_th5_param) <= 1, "ERRO: Argumento do acos do Theta 5 e maior que 1, solucao invalida"
    theta5 = np.acos(acos_th5_param)

    '''
    # Se o pulso estiver pra cima:
    current_theta5 = dh[4, 3]
    if(current_theta5 < 0):
        theta5 *= -1
    '''
    theta5 = wrap_angle(theta5 + offset[4])

    # Calculo do Theta 6
    T_6_0 = reverse_transformation_matrix(T_0_6)
    X60x = T_6_0[0, 0]
    X60y = T_6_0[1, 0]
    Y60x = T_6_0[0, 1]
    Y60y = T_6_0[1, 1]
    atan_th6_first = -X60y*np.sin(theta1-offset[0]) + Y60y*np.cos(theta1-offset[0])
    atan_th6_second = X60x*np.sin(theta1-offset[0]) - Y60x*np.cos(theta1-offset[0])
    if np.sin(theta5) == 0 or (atan_th6_first == 0 and atan_th6_second == 0):
        theta6 = 0
    else:        
        theta6 = np.atan2(atan_th6_first/np.sin(theta5), atan_th6_second/np.sin(theta5))  
    theta6 = wrap_angle(theta6 + offset[5])

    # Calculo do Theta 3
    a1 = dh[0, 0]
    alpha1 = dh[0, 1]
    d1 = dh[0, 2]
    a5 = dh[4, 0]
    alpha5 = dh[4, 1]
    d5 = dh[4, 2]
    a6 = dh[5, 0]
    alpha6 = dh[5, 1]
    d6 = dh[5, 2]
    T_0_1 = mount_ai_matrix(a1, alpha1, d1, theta1 - offset[0])
    T_6_1 = np.matmul(T_6_0, T_0_1)
    T_1_6 = reverse_transformation_matrix(T_6_1)
    T_4_5 = mount_ai_matrix(a5, alpha5, d5, theta5 - offset[4])
    T_5_6 = mount_ai_matrix(a6, alpha6, d6, theta6 - offset[5])
    T_4_6 = np.matmul(T_4_5, T_5_6)
    T_6_4 = reverse_transformation_matrix(T_4_6)
    T_1_4 = np.matmul(T_1_6, T_6_4)
    p14x = T_1_4[0, 3]
    p14y = T_1_4[1, 3]
    p14xy = np.sqrt(p14x**2 + p14y**2)
    a2 = dh[1, 0]
    a3 = dh[2, 0]
    acos_arg = (p14xy**2 - a2**2 - a3**2)/(2*a2*a3)
    if(acos_arg > 1):
        theta3 = 0
    else:
        theta3 = np.acos(acos_arg)
        '''
        # Se cotovelo estiver para baixo:
        current_theta3 = dh[2, 3]
        if(current_theta3 <= 0):
            theta3 *= -1
        '''
    theta3 = wrap_angle(theta3 + offset[2])

    # Calculo do Theta 2
    delta = np.atan2(-p14y, p14x)
    epsilon = np.acos((p14xy**2 + a2**2 - a3**2)/(2*a2*p14xy))
    #theta2 = np.atan2(p14y, -p14x) - np.asin((a3*np.sin(theta3))/p14xy) + np.pi/2
    theta2 = delta - epsilon
    theta2 = wrap_angle(theta2 + offset[1])

    # Calculo de Theta 4
    alpha2 = dh[1, 1]
    d2 = dh[1, 2]
    alpha3 = dh[2, 1]
    d3 = dh[2, 2]
    T_1_2 = mount_ai_matrix(a2, alpha2, d2, theta2 - offset[1])
    T_2_3 = mount_ai_matrix(a3, alpha3, d3, theta3 - offset[2])
    T_0_3 = np.matmul(np.matmul(T_0_1, T_1_2), T_2_3)
    T_3_0 = reverse_transformation_matrix(T_0_3)
    T_0_4 = np.matmul(T_0_6, T_6_4)
    T_3_4 = np.matmul(T_3_0, T_0_4)
    X34x = T_3_4[0, 0]
    X34y = T_3_4[1, 0]
    theta4 = np.atan2(X34y, X34x)
    theta4 = wrap_angle(theta4 + offset[3])

    T_0_1_check = mount_ai_matrix(dh[0, 0], dh[0, 1], dh[0, 2], theta1)
    T_1_2_check = mount_ai_matrix(dh[1, 0], dh[1, 1], dh[1, 2], theta2)
    T_2_3_check = mount_ai_matrix(dh[2, 0], dh[2, 1], dh[2, 2], theta3)
    T_3_4_check = mount_ai_matrix(dh[3, 0], dh[3, 1], dh[3, 2], theta4)
    T_4_5_check = mount_ai_matrix(dh[4, 0], dh[4, 1], dh[4, 2], theta5)
    T_5_6_check = mount_ai_matrix(dh[5, 0], dh[5, 1], dh[5, 2], theta6)

    T_0_3_check = np.matmul(T_0_1_check, np.matmul(T_1_2_check, T_2_3_check))
    T_3_6_check = np.matmul(T_3_4_check, np.matmul(T_4_5_check, T_5_6_check))
    T_0_6_check = np.matmul(T_0_3_check, T_3_6_check)

    #print(T_0_6_check)
    #print()
    #print(T_0_6)
    #print()

    #print_matrix(T_3_4)

    joint_values = np.array([wrap_angle(theta1),
                             wrap_angle(theta2),
                             wrap_angle(theta3),
                             wrap_angle(theta4),
                             wrap_angle(theta5),
                             wrap_angle(theta6)
                            ])

    return joint_values

# Validacao Cinematica Inversa
def ik_validate(test_cases, num_teste):
    TOLERANCE_POS = 0.03    # Error tolerance in meters
    TOLERANCE_ORIENT = 0.03 # Error tolerance in radians

    sleep(1)

    target_pose = test_cases[num_teste]
    target_matrix = pose2matrix(target_pose)
    theta_values = ik_calculate(target_matrix)
    joints = get_joints()
    end_effector = sim.getObject("/UR5/JacoHand")
    #end_effector = sim.getObject("/UR5/connection")

    base_matrix = sim.getObjectMatrix(sim.getObject("/UR5"))
    base_matrix = np.array([base_matrix[0:4],
                            base_matrix[4:8],
                            base_matrix[8:12],
                            [0, 0, 0, 1]])

    fail_count = 0

    print(f"========================================================")
    print(f"Validacao Cinematica Inversa - Caso teste {num_teste+1}")
    print(f"========================================================")

    for joint, value in zip(joints, theta_values):
        sim.setJointPosition(joint, value)
    end_orient = sim.getObjectOrientation(end_effector)
    end_orient = np.array(sim.alphaBetaGammaToYawPitchRoll(end_orient[0],
                                                           end_orient[1],
                                                           end_orient[2]))
    end_ground = np.array([sim.getObjectPosition(end_effector),
                          end_orient[::-1]]).reshape((-1))

    end_diff = np.array([
                         target_pose[0] - end_ground[0],
                         target_pose[1] - end_ground[1], 
                         target_pose[2] - end_ground[2],
                         target_pose[3] - end_ground[3],
                         target_pose[4] - end_ground[4], 
                         target_pose[5] - end_ground[5],
                         ])
    print(f"Angulos das Juntas: {theta_values}")
    print(f"Pose Desejada (X, Y, Z, R, P, Y): {target_pose}")
    print(f"Truth (X, Y, Z, R, P, Y):         {end_ground}")
    print(f"Diff (X, Y, Z, R, P, Y):          {end_diff}")
    for i in range(len(end_diff)):
        if(i <= 2):
            if abs(end_diff[i]) > TOLERANCE_POS or np.isnan(end_diff[i]):
                fail_count += 1
                axis = ''
                if(i == 0):
                    axis = 'X'
                elif(i == 1):
                    axis = 'Y'
                elif(i == 2):
                    axis = 'Z'
                print(f"FALHA: Diferenca de posicao do eixo {axis} fora da faixa de tolerancia")
        else:
            if abs(end_diff[i]) > TOLERANCE_ORIENT or np.isnan(end_diff[i]):
                fail_count += 1
                axis = ''
                if(i == 3):
                    axis = 'Roll'
                elif(i == 4):
                    axis = 'Pitch'
                elif(i == 5):
                    axis = 'Yaw'
                print(f"FALHA: Diferenca de orientacao ({axis}) fora da faixa de tolerancia")
    print(f"--------------------------------------------------------")
    
    if(fail_count == 0):
        print(f"Caso teste {num_teste+1} validado com exito.")
    else:
        print(f"Caso teste {num_teste+1} FALHOU com {fail_count} erros.")
    print(f"========================================================")
    print()
