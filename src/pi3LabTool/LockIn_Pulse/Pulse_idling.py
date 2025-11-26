import spinapi as sp

def idling(t_ini,f_LIA):
    CLOCK_FREQ_MHZ = 200

    #Pulse Sequence
    factor = 1e9*sp.ns
    print("Initializing PulseBlaster...")
    # It's good practice to close any existing connection before starting.
    try:
        sp.pb_close()
    except Exception:
        pass  # Ignore error if board was not open.

    # Initialize the connection to the board.
    if sp.pb_init() != 0:
        print(f"Error initializing PulseBlaster: {sp.pb_get_error()}")
        exit()
    sp.pb_core_clock(CLOCK_FREQ_MHZ)
    sp.pb_start_programming(sp.PULSE_PROGRAM)
    start = sp.pb_inst_pbonly(0b000000000001100,sp.CONTINUE,0,t_ini*factor)
    sp.pb_inst_pbonly(0b000000000000100,sp.CONTINUE,0,(1/(2*f_LIA)-t_ini)*factor)
    sp.pb_inst_pbonly(0b000000000001000,sp.CONTINUE,0,t_ini*factor)
    sp.pb_inst_pbonly(0b000000000000000,sp.BRANCH,start,(1/(2*f_LIA)-t_ini)*factor)
    sp.pb_stop_programming()
    sp.pb_reset()
    sp.pb_start()

    #sp.pb_stop()
    sp.pb_close()

def finish(t_ini,f_LIA):
    CLOCK_FREQ_MHZ = 200

    #Pulse Sequence
    factor = 1e9*sp.ns
    print("Initializing PulseBlaster...")
    # It's good practice to close any existing connection before starting.
    try:
        sp.pb_close()
    except Exception:
        pass  # Ignore error if board was not open.

    # Initialize the connection to the board.
    if sp.pb_init() != 0:
        print(f"Error initializing PulseBlaster: {sp.pb_get_error()}")
        exit()
    sp.pb_core_clock(CLOCK_FREQ_MHZ)
    sp.pb_start_programming(sp.PULSE_PROGRAM)
    start = sp.pb_inst_pbonly(0b000000000001100,sp.CONTINUE,0,t_ini*factor)
    sp.pb_inst_pbonly(0b000000000000100,sp.CONTINUE,0,(1/(2*f_LIA)-t_ini)*factor)
    sp.pb_inst_pbonly(0b000000000001000,sp.CONTINUE,0,t_ini*factor)
    sp.pb_inst_pbonly(0b000000000000000,sp.BRANCH,start,(1/(2*f_LIA)-t_ini)*factor)
    sp.pb_stop_programming()
    sp.pb_reset()
    sp.pb_start()

    sp.pb_stop()
    sp.pb_close()

if __name__ == '__main__':
    t_ini = 40e-6
    f_LIA = 10e3
    #idling(t_ini,f_LIA)
    finish(t_ini,f_LIA)