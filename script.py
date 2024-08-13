'''
PPGEE - Departamento de Engenharia Eletrica e de Computacao - UFBA
UR5: Cinematica Direta, Inversa e Planejamento de Trajetoria
Alunos: Andre Paiva Conrado Rodrigues e Gabriel Lucas Nascimento Silva
Disciplina: Sistemas Roboticos - 2024.1
Data: 11 ago 2024
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

FLAG_DK = False # Flag que indica se a validacao da C.D. foi concluida
COUNTER_DK = 0 # Contador de casos de teste da C.D. que passaram por validacao

# Array de casos de teste da C.D (J1, J2, J3, J4, J5, J6)
TESTES_DH = np.array([
                        [   0,      0,      0,      0,      0,       0    ],
                        [   30,     60,     90,     0,      0,       0    ],
                        [   0,      0,      0,      30,     60,      90   ],
                        [   -45,    -30,    60,     15,     -30,     75   ],
                        [   45,     -90,    75,     30,     -25,     -90  ],
                        [   39,     42,     -80,    9,      -112,    13   ],
                        [   -158,   97,     45,    -138,    125,     -147 ],
                        [   130,    -20,    -50,    -45,    25,      110  ],
                    ])

NUM_TESTES_DH = TESTES_DH.shape[0] # Quantidade de casos de teste da C.D.

#-----------------------------------------------#
#-------------Interacao CoppeliaSim-------------#
#-----------------------------------------------#

# Inicializacao
def sysCall_init():
    sim = require('sim')
    joints = get_joints()
    for joint in joints:
        sim.setJointMode(joint, sim.jointmode_kinematic, 1)

# Validacoes implementadas no sensing
def sysCall_sensing():
    global FLAG_DK, COUNTER_DK, TESTES_DH, NUM_TESTES_DH

    if(not FLAG_DK):
        dk_validate(TESTES_DH, COUNTER_DK)
        COUNTER_DK += 1
        if(COUNTER_DK >= NUM_TESTES_DH):
            FLAG_DK = True

# Atuacao step-by-step
def sysCall_actuation():
    global SIGNAL
    
    if(FLAG_DK):
        joints = get_joints()
        for joint in joints:
            orient = sim.getJointPosition(joint)
            if(orient > np.pi/2):
                SIGNAL = False
            elif(orient < -np.pi/2):
                SIGNAL = True
            if(SIGNAL):
                orient += 0.005
            else:
                orient -= 0.005
            sim.setJointPosition(joint, orient)

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
    return theta

# Limita angulo entre -pi e pi
def wrap_angle(angle):
    return np.atan2(np.sin(angle),np.cos(angle))

# Gera matriz de transformacao reversa
def reverse_transformation_matrix(matrix):
    rev_matrix = np.identity(4)
    rev_matrix[:3, :3] = matrix[:3, :3].T
    rev_matrix[:3, 3] = np.matmul(rev_matrix[:3, :3], matrix[:3, 3]) * (-1)
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

#-----------------------------------------------#
#---------Funcoes de Cinematica Direta----------#
#-----------------------------------------------#

# Tabela DH (a, alpha, d, theta)
def dk_get_dh():
    theta = read_joints_sensors()
    dh = np.array([ [    0,             -np.pi/2,   89.16e-3,  theta[0] + np.pi/2  ], # A1
                    [    425e-3,        0,          0,         theta[1] - np.pi/2  ], # A2
                    [    392.25e-3,     0,          109.15e-3, theta[2]            ], # A3
                    [    0,             -np.pi/2,   0,         theta[3] - np.pi/2  ], # A4
                    [    0,             np.pi/2,    94.65e-3,  theta[4]            ], # A5
                    [    0,             0,          82.3e-3,   theta[5]            ], # A6
                 ])
    return dh

# Matriz Ai
def dk_get_ai(i):
    if i < 1 or i > 6:
        raise Exception('i deve estar entre 1 e 6')
    else:
        dh_line = dk_get_dh()[i-1]
        ai = dh_line[0]
        di = dh_line[2]
        s_alp = np.sin(dh_line[1])
        c_alp = np.cos(dh_line[1])
        s_the = np.sin(dh_line[3])
        c_the = np.cos(dh_line[3])
        matrix = np.array([ [ c_the,    -s_the*c_alp,   s_the*s_alp,    ai*c_the ],
                            [ s_the,    c_the*c_alp,    -c_the*s_alp,   ai*s_the ],
                            [ 0,        s_alp,          c_alp,          di       ],
                            [ 0,        0,              0,              1        ]])
        return matrix
        
# Matriz de transformacao completa
def dk_get_transformation_matrix():
    t_matrix = np.identity(4)
    for i in range(1, 7):
        t_matrix = np.matmul(t_matrix, dk_get_ai(i))
    return t_matrix

# Posicao da garra
def dk_get_end_effector_pose():
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

    end_effector = sim.getObject("/UR5/connection")
    joints = get_joints()
    fail_count = 0

    print(f"========================================================")
    print(f"Validacao - Cinematica Direta - Caso teste {num_teste+1}")
    print(f"========================================================")

    for joint, value in zip(joints, test_cases[num_teste]):
        sim.setJointPosition(joint, value*np.pi/180.0)
    end_pose = dk_get_end_effector_pose()
    end_ground = sim.getObjectPosition(end_effector)
    end_diff = [end_pose[0][3] - end_ground[0],
                end_pose[1][3] - end_ground[1], 
                end_pose[2][3] - end_ground[2], ]
    print(f"Angulos das Juntas: {test_cases[num_teste]}")
    print(f"Calculo: X={end_pose[0][3]:.7f} \t Y={end_pose[1][3]:.7f} \t Z={end_pose[2][3]:.7f}")
    print(f"Truth:   X={end_ground[0]:.7f} \t Y={end_ground[1]:.7f} \t Z={end_ground[2]:.7f}")
    print(f"Diff:    X={end_diff[0]:.7f} \t Y={end_diff[1]:.7f} \t Z={end_diff[2]:.7f}")
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

    sleep(1)
    
    if(num_teste >= test_cases.shape[0] - 1):
        for joint, value in zip(joints, test_cases[num_teste]):
            sim.setJointPosition(joint, 0)
    else:
        for joint, value in zip(joints, test_cases[num_teste+1]):
            sim.setJointPosition(joint, value*np.pi/180.0)

#-----------------------------------------------#
#--------Funcoes de Cinematica Inversa----------#
#-----------------------------------------------#

'''
# Calcular Cinematica Inversa com base em target pose
# Target: (X, Y, Z, R, P, Y)
def ik_calculate(target_pose):
    target_matrix = pose2matrix(target_pose)
    base_matrix = sim.getObjectMatrix(sim.getObject("/UR5"))
    
    t_0_6 = 


    t_6_5 = reverse_transformation_matrix(dk_get_ai(6))
    t_0_5
'''