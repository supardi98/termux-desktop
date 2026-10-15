#define _GNU_SOURCE
#include <dlfcn.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>

static int (*real_chown)(const char *, uid_t, gid_t) = NULL;
static int (*real_chmod)(const char *, mode_t) = NULL;

__attribute__((constructor)) static void init(void) {
    // Unset LD_PRELOAD so child shells/processes run cleanly
    unsetenv("LD_PRELOAD");
}

int chown(const char *pathname, uid_t owner, gid_t group) {
    if (pathname && strncmp(pathname, "/dev/pts/", 9) == 0) {
        return 0;
    }
    if (!real_chown) real_chown = (int (*)(const char *, uid_t, gid_t))dlsym(RTLD_NEXT, "chown");
    return real_chown ? real_chown(pathname, owner, group) : 0;
}

int chmod(const char *pathname, mode_t mode) {
    if (pathname && strncmp(pathname, "/dev/pts/", 9) == 0) {
        return 0;
    }
    if (!real_chmod) real_chmod = (int (*)(const char *, mode_t))dlsym(RTLD_NEXT, "chmod");
    return real_chmod ? real_chmod(pathname, mode) : 0;
}
